from datetime import datetime, timezone as dt_timezone

from .feed_ingestion import _json_request
from .models import WorldEvent


GDACS_URL = "https://www.gdacs.org/gdacsapi/api/Events/geteventlist/EVENTS4APP"
USGS_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_week.geojson"
EONET_URL = "https://eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=200"

GDACS_EVENT_TYPES = {
    "EQ": WorldEvent.EventType.EARTHQUAKE,
    "TC": WorldEvent.EventType.CYCLONE,
    "FL": WorldEvent.EventType.FLOOD,
    "VO": WorldEvent.EventType.VOLCANO,
    "WF": WorldEvent.EventType.WILDFIRE,
    "DR": WorldEvent.EventType.DROUGHT,
}

GDACS_ALERT_LEVELS = {
    "green": WorldEvent.AlertLevel.GREEN,
    "orange": WorldEvent.AlertLevel.ORANGE,
    "red": WorldEvent.AlertLevel.RED,
}

EONET_EVENT_TYPES = {
    "wildfires": WorldEvent.EventType.WILDFIRE,
    "severeStorms": WorldEvent.EventType.SEVERE_STORM,
    "volcanoes": WorldEvent.EventType.VOLCANO,
    "floods": WorldEvent.EventType.FLOOD,
    "drought": WorldEvent.EventType.DROUGHT,
}


def _parse_datetime(value):
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt_timezone.utc)
    return parsed


def _upsert_world_event(source, external_id, **fields):
    external_id = str(external_id)[:180]
    obj, created = WorldEvent.objects.update_or_create(
        source=source, external_id=external_id, defaults=fields
    )
    return "created" if created else "updated"


def _gdacs_population(properties):
    data = properties.get("populationdata")
    if isinstance(data, list) and data:
        data = data[0]
    if isinstance(data, dict):
        value = data.get("value") or data.get("population")
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
    return None


def sync_gdacs():
    payload = _json_request(GDACS_URL)
    features = payload.get("features", []) if isinstance(payload, dict) else []
    totals = {"created": 0, "updated": 0}
    for feature in features:
        properties = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates") or []
        event_id = properties.get("eventid")
        if not event_id or len(coordinates) < 2:
            continue
        severity = properties.get("severitydata") or {}
        url = (properties.get("url") or {}).get("report", "")
        result = _upsert_world_event(
            WorldEvent.Source.GDACS,
            event_id,
            event_type=GDACS_EVENT_TYPES.get(
                properties.get("eventtype"), WorldEvent.EventType.OTHER
            ),
            alert_level=GDACS_ALERT_LEVELS.get(
                str(properties.get("alertlevel") or "").lower(),
                WorldEvent.AlertLevel.UNKNOWN,
            ),
            title=str(properties.get("name") or "Untitled event")[:240],
            description=str(
                properties.get("description") or severity.get("severitytext") or ""
            )[:2000],
            country=str(properties.get("country") or "")[:160],
            latitude=coordinates[1],
            longitude=coordinates[0],
            severity_value=severity.get("severity"),
            severity_unit=str(severity.get("severityunit") or "")[:20],
            population_affected=_gdacs_population(properties),
            url=str(url)[:500],
            event_from=_parse_datetime(properties.get("fromdate")),
            event_to=_parse_datetime(properties.get("todate")),
            published_at=_parse_datetime(properties.get("fromdate")),
            raw_payload=properties,
            is_active=True,
        )
        totals[result] += 1
    return totals


def sync_usgs_global():
    payload = _json_request(USGS_URL)
    features = payload.get("features", []) if isinstance(payload, dict) else []
    totals = {"created": 0, "updated": 0}
    for feature in features:
        properties = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates") or []
        feature_id = feature.get("id")
        if not feature_id or len(coordinates) < 2:
            continue
        magnitude = properties.get("mag")
        alert_level = WorldEvent.AlertLevel.GREEN
        if isinstance(magnitude, (int, float)):
            if magnitude >= 6.5:
                alert_level = WorldEvent.AlertLevel.RED
            elif magnitude >= 5.5:
                alert_level = WorldEvent.AlertLevel.ORANGE
        time_ms = properties.get("time")
        occurred_at = (
            datetime.fromtimestamp(time_ms / 1000, tz=dt_timezone.utc)
            if isinstance(time_ms, (int, float))
            else None
        )
        result = _upsert_world_event(
            WorldEvent.Source.USGS,
            feature_id,
            event_type=WorldEvent.EventType.EARTHQUAKE,
            alert_level=alert_level,
            title=str(
                properties.get("title") or properties.get("place") or "Earthquake"
            )[:240],
            description=str(properties.get("place") or "")[:2000],
            country="",
            latitude=coordinates[1],
            longitude=coordinates[0],
            severity_value=magnitude,
            severity_unit="M",
            population_affected=None,
            url=str(properties.get("url") or "")[:500],
            event_from=occurred_at,
            event_to=occurred_at,
            published_at=occurred_at,
            raw_payload=properties,
            is_active=True,
        )
        totals[result] += 1
    return totals


def _eonet_point(geometries):
    for entry in reversed(geometries or []):
        geo_type = entry.get("type")
        coords = entry.get("coordinates")
        if geo_type == "Point" and coords and len(coords) >= 2:
            return entry, coords[0], coords[1]
        if geo_type == "Polygon" and coords:
            ring = coords[0] if coords and isinstance(coords[0], list) else []
            points = [p for p in ring if isinstance(p, list) and len(p) >= 2]
            if points:
                longitude = sum(p[0] for p in points) / len(points)
                latitude = sum(p[1] for p in points) / len(points)
                return entry, longitude, latitude
    return None, None, None


def sync_eonet():
    payload = _json_request(EONET_URL)
    events = payload.get("events", []) if isinstance(payload, dict) else []
    totals = {"created": 0, "updated": 0}
    for event in events:
        event_id = event.get("id")
        if not event_id:
            continue
        categories = event.get("categories") or []
        category_id = categories[0].get("id") if categories else None
        entry, longitude, latitude = _eonet_point(event.get("geometry") or [])
        if longitude is None or latitude is None:
            continue
        magnitude = entry.get("magnitudeValue") if entry else None
        unit = entry.get("magnitudeUnit") if entry else ""
        occurred_at = _parse_datetime(entry.get("date")) if entry else None
        sources = event.get("sources") or []
        url = event.get("link") or (sources[0].get("url") if sources else "")
        result = _upsert_world_event(
            WorldEvent.Source.EONET,
            event_id,
            event_type=EONET_EVENT_TYPES.get(category_id, WorldEvent.EventType.OTHER),
            alert_level=WorldEvent.AlertLevel.UNKNOWN,
            title=str(event.get("title") or "Untitled event")[:240],
            description=str(event.get("description") or "")[:2000],
            country="",
            latitude=latitude,
            longitude=longitude,
            severity_value=magnitude,
            severity_unit=str(unit or "")[:20],
            population_affected=None,
            url=str(url or "")[:500],
            event_from=occurred_at,
            event_to=None,
            published_at=occurred_at,
            raw_payload=event,
            is_active=event.get("closed") is None,
        )
        totals[result] += 1
    return totals


def sync_world_events():
    results = {}
    for name, sync_fn in (
        ("gdacs", sync_gdacs),
        ("usgs", sync_usgs_global),
        ("eonet", sync_eonet),
    ):
        try:
            results[name] = {"ok": True, **sync_fn()}
        except Exception as exc:
            results[name] = {"ok": False, "error": str(exc)}
    return results
