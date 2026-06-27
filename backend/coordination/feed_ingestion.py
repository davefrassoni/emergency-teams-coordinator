import hashlib
import json
from datetime import datetime, timezone as dt_timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.db import transaction
from django.utils import timezone

from .models import (
    Activity,
    Emergency,
    FeedRecord,
    FeedSource,
    MissingPersonReport,
)
from .realtime import broadcast_situation_change


PUBLIC_FIELDS = {
    "id",
    "nombre",
    "estado",
    "ubicacion",
    "fecha",
    "descripcion",
    "primerNombre",
    "segundoNombre",
    "primerApellido",
    "segundoApellido",
    "edad",
    "edadAproximada",
    "vestimenta",
    "direccion",
    "ubicacionEstado",
    "ubicacionMunicipio",
    "ubicacionParroquia",
    "createdAt",
    "updatedAt",
    "latitud",
    "longitud",
    "latitude",
    "longitude",
}


def _json_request(url, authorization_header=""):
    headers = {
        "Accept": "application/json",
        "User-Agent": "ReliefGridFeedWorker/1.0 (+https://davefrassoni.com/emergency/)",
    }
    if authorization_header:
        if ":" in authorization_header:
            key, value = authorization_header.split(":", 1)
            headers[key.strip()] = value.strip()
        else:
            headers["Authorization"] = authorization_header
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read(500).decode("utf-8", errors="replace")
        raise RuntimeError(f"Feed returned HTTP {exc.code}: {body}") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Feed request failed: {exc}") from exc


def _safe_payload(payload):
    return {key: payload.get(key) for key in PUBLIC_FIELDS if key in payload}


def _number(payload, *keys):
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
    return None


def _timestamp(value):
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        seconds = value / 1000 if value > 10_000_000_000 else value
        return datetime.fromtimestamp(seconds, tz=dt_timezone.utc)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _person_name(payload):
    explicit = str(payload.get("nombre") or "").strip()
    if explicit:
        return explicit
    return " ".join(
        str(payload.get(key) or "").strip()
        for key in [
            "primerNombre",
            "segundoNombre",
            "primerApellido",
            "segundoApellido",
        ]
        if str(payload.get(key) or "").strip()
    ) or "Unidentified person"


def _location(payload):
    explicit = str(payload.get("ubicacion") or payload.get("direccion") or "").strip()
    if explicit:
        return explicit
    return ", ".join(
        str(payload.get(key) or "").strip()
        for key in ["ubicacionParroquia", "ubicacionMunicipio", "ubicacionEstado"]
        if str(payload.get(key) or "").strip()
    ) or "Venezuela · location not specified"


def _age(payload):
    value = payload.get("edadAproximada", payload.get("edad"))
    try:
        parsed = int(value)
        return parsed if 0 <= parsed <= 130 else None
    except (TypeError, ValueError):
        return None


@transaction.atomic
def _upsert_missing_person(source, payload):
    safe = _safe_payload(payload)
    external_id = str(safe.get("id") or "").strip()
    if not external_id:
        external_id = hashlib.sha256(
            json.dumps(safe, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()[:32]
    content_hash = hashlib.sha256(
        json.dumps(safe, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    record = (
        FeedRecord.objects.select_for_update()
        .filter(source=source, external_id=external_id)
        .first()
    )
    if record and record.content_hash == content_hash:
        record.save(update_fields=["last_seen_at"])
        return "unchanged"

    name = _person_name(safe)
    location = _location(safe)
    located = str(safe.get("estado") or "").lower() in {
        "localizado",
        "located",
        "found",
    }
    latitude = _number(safe, "latitud", "latitude")
    longitude = _number(safe, "longitud", "longitude")
    source_url = f"{source.source_url.rstrip('/')}/p/{external_id}"

    if record and record.emergency:
        emergency = record.emergency
        emergency.title = f"Missing person: {name}"
        emergency.location = location
        emergency.latitude = latitude
        emergency.longitude = longitude
        emergency.status = (
            Emergency.Status.RESOLVED if located else Emergency.Status.REPORTED
        )
        emergency.details = str(safe.get("descripcion") or "")
        emergency.save()
        report, _ = MissingPersonReport.objects.get_or_create(
            emergency=emergency, defaults={"person_name": name}
        )
        action = "updated"
    else:
        emergency = Emergency.objects.create(
            situation=source.situation,
            title=f"Missing person: {name}",
            location=location,
            latitude=latitude,
            longitude=longitude,
            source=Emergency.Source.EXTERNAL_FEED,
            status=Emergency.Status.RESOLVED if located else Emergency.Status.REPORTED,
            triage=Emergency.Triage.UNKNOWN,
            people_affected=1,
            details=str(safe.get("descripcion") or ""),
            created_by=None,
        )
        report = MissingPersonReport(emergency=emergency, person_name=name)
        action = "created"

    report.person_name = name
    report.approximate_age = _age(safe)
    report.physical_description = str(safe.get("descripcion") or "")
    report.clothing = str(safe.get("vestimenta") or "")
    report.circumstances = f"Imported from {source.name}. Verify with the source."
    report.last_seen_at = _timestamp(safe.get("fecha"))
    report.save()

    if record:
        record.content_hash = content_hash
        record.raw_payload = safe
        record.source_url = source_url
        record.emergency = emergency
        record.save()
    else:
        FeedRecord.objects.create(
            source=source,
            external_id=external_id,
            content_hash=content_hash,
            source_url=source_url,
            raw_payload=safe,
            emergency=emergency,
        )
    return action


def sync_venezuela_missing(source):
    base = source.api_url.rstrip("/")
    if not base:
        raise RuntimeError("The feed API URL is not configured.")
    totals = {"created": 0, "updated": 0, "unchanged": 0}
    page = 1
    while page <= 100:
        query = urlencode({"page": page, "pageSize": 100})
        payload = _json_request(
            f"{base}/personas?{query}",
            source.authorization_header,
        )
        items = payload.get("items", []) if isinstance(payload, dict) else []
        for item in items:
            result = _upsert_missing_person(source, item)
            totals[result] += 1
        total_pages = int(payload.get("totalPages") or 0) if isinstance(payload, dict) else 0
        if not items or page >= total_pages:
            break
        page += 1
    return totals


def sync_source(source):
    source.last_checked_at = timezone.now()
    try:
        if source.adapter == FeedSource.Adapter.VENEZUELA_MISSING:
            result = sync_venezuela_missing(source)
        else:
            raise RuntimeError(f"Unsupported feed adapter: {source.adapter}")
        source.last_success_at = timezone.now()
        source.last_error = ""
        source.save(
            update_fields=[
                "last_checked_at",
                "last_success_at",
                "last_error",
                "updated_at",
            ]
        )
        changed = result.get("created", 0) + result.get("updated", 0)
        if changed:
            activity = Activity.objects.create(
                situation=source.situation,
                actor=None,
                action="EXTERNAL_FEED_SYNCED",
                message=f"{source.name}: {changed} external reports imported or updated",
            )
            broadcast_situation_change(source.situation_id, activity.pk)
        return result
    except Exception as exc:
        source.last_error = str(exc)[:4000]
        source.save(
            update_fields=["last_checked_at", "last_error", "updated_at"]
        )
        raise

