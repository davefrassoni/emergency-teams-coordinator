<script setup>
import { nextTick, onBeforeUnmount, onMounted, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const props = defineProps({
  emergencies: { type: Array, default: () => [] },
  selecting: { type: Boolean, default: false },
  selectedPoint: { type: Object, default: null },
  supplyRequests: { type: Array, default: () => [] },
})
const emit = defineEmits(['select'])

let map
let markersLayer
let selectionMarker
const markers = new Map()
let fitted = false

const markerClass = {
  RED: 'map-marker--red',
  YELLOW: 'map-marker--yellow',
  GREEN: 'map-marker--green',
  BLACK: 'map-marker--black',
  UNKNOWN: 'map-marker--unknown',
}

function markerIcon(triage, isPublic) {
  return L.divIcon({
    className: 'map-marker-wrap',
    html: `<span class="map-marker ${markerClass[triage] || markerClass.UNKNOWN}${isPublic ? ' map-marker--public' : ''}"><i></i></span>`,
    iconSize: [30, 36],
    iconAnchor: [15, 33],
    popupAnchor: [0, -31],
  })
}

function supplyIcon(kind) {
  return L.divIcon({
    className: 'map-marker-wrap',
    html: `<span class="supply-map-marker supply-map-marker--${kind}"><i>${kind === 'delivery' ? '→' : '+'}</i></span>`,
    iconSize: [34, 38],
    iconAnchor: [17, 35],
    popupAnchor: [0, -33],
  })
}

function missingPersonIcon() {
  return L.divIcon({
    className: 'map-marker-wrap',
    html: '<span class="missing-map-marker"><i>?</i></span>',
    iconSize: [34, 38],
    iconAnchor: [17, 35],
    popupAnchor: [0, -33],
  })
}

function popupContent(item) {
  const root = document.createElement('div')
  root.className = 'map-popup'
  const badge = document.createElement('span')
  badge.textContent = item.missing_person
    ? 'Missing person · awaiting verification'
    : item.source === 'PUBLIC' && item.status === 'REPORTED'
      ? 'Awaiting verification'
      : item.triage_label
  const title = document.createElement('strong')
  title.textContent = item.title
  const location = document.createElement('small')
  location.textContent = item.location
  root.append(badge, title, location)
  return root
}

function supplyPopup(request, commitment = null) {
  const root = document.createElement('div')
  root.className = 'map-popup'
  const badge = document.createElement('span')
  badge.textContent = commitment ? commitment.status_label : 'Supplies needed'
  const title = document.createElement('strong')
  title.textContent = commitment
    ? `${commitment.contributor_name} delivery`
    : request.title
  const detail = document.createElement('small')
  detail.textContent = commitment
    ? commitment.current_location || `Going to ${request.delivery_location}`
    : request.items
        .filter((item) => Number(item.remaining_quantity) > 0)
        .map((item) => `${item.remaining_quantity} ${item.unit_label} ${item.name}`)
        .join(' · ')
  root.append(badge, title, detail)
  return root
}

function renderMarkers() {
  if (!map || !markersLayer) return
  markersLayer.clearLayers()
  markers.clear()
  const bounds = []
  props.emergencies.forEach((item) => {
    if (item.latitude == null || item.longitude == null) return
    const point = [Number(item.latitude), Number(item.longitude)]
    if (!Number.isFinite(point[0]) || !Number.isFinite(point[1])) return
    const marker = L.marker(point, {
      icon: item.missing_person
        ? missingPersonIcon()
        : markerIcon(item.triage, item.source === 'PUBLIC' && item.status === 'REPORTED'),
      title: item.title,
      alt: `Emergency: ${item.title}`,
      keyboard: true,
    })
      .bindPopup(popupContent(item))
      .addTo(markersLayer)
    markers.set(item.id, marker)
    bounds.push(point)
  })
  props.supplyRequests.forEach((request) => {
    const destination = [Number(request.latitude), Number(request.longitude)]
    if (destination.every(Number.isFinite)) {
      const marker = L.marker(destination, {
        icon: supplyIcon('need'),
        title: `Supplies needed: ${request.title}`,
        alt: `Supply request: ${request.title}`,
        keyboard: true,
      })
        .bindPopup(supplyPopup(request))
        .addTo(markersLayer)
      markers.set(`supply:${request.id}`, marker)
      bounds.push(destination)
    }
    request.commitments.forEach((commitment) => {
      if (commitment.current_latitude == null || commitment.current_longitude == null) return
      const point = [Number(commitment.current_latitude), Number(commitment.current_longitude)]
      if (!point.every(Number.isFinite)) return
      const marker = L.marker(point, {
        icon: supplyIcon('delivery'),
        title: `Supply delivery by ${commitment.contributor_name}`,
        alt: `Tracked supply delivery by ${commitment.contributor_name}`,
        keyboard: true,
      })
        .bindPopup(supplyPopup(request, commitment))
        .addTo(markersLayer)
      markers.set(`delivery:${commitment.id}`, marker)
      bounds.push(point)
    })
  })
  if (!fitted && bounds.length) {
    map.fitBounds(bounds, { padding: [45, 45], maxZoom: 14 })
    fitted = true
  }
}

function renderSelection() {
  if (!map) return
  if (selectionMarker) {
    selectionMarker.remove()
    selectionMarker = null
  }
  if (props.selectedPoint) {
    selectionMarker = L.circleMarker(
      [props.selectedPoint.latitude, props.selectedPoint.longitude],
      {
        radius: 10,
        color: '#fff',
        weight: 3,
        fillColor: '#de542f',
        fillOpacity: 1,
      },
    ).addTo(map)
    map.panTo(selectionMarker.getLatLng())
  }
}

onMounted(async () => {
  await nextTick()
  map = L.map('public-situation-map', { zoomControl: true }).setView([8.2, -66.3], 6)
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors',
  }).addTo(map)
  markersLayer = L.layerGroup().addTo(map)
  map.on('click', (event) => {
    if (props.selecting) {
      emit('select', {
        latitude: Number(event.latlng.lat.toFixed(6)),
        longitude: Number(event.latlng.lng.toFixed(6)),
      })
    }
  })
  renderMarkers()
  renderSelection()
})

watch(() => props.emergencies, renderMarkers, { deep: true })
watch(() => props.supplyRequests, renderMarkers, { deep: true })
watch(() => props.selectedPoint, renderSelection, { deep: true })
watch(() => props.selecting, (selecting) => {
  if (map) map.getContainer().classList.toggle('map--selecting', selecting)
})

function focusEmergency(id) {
  const marker = markers.get(id)
  if (marker) {
    map.setView(marker.getLatLng(), Math.max(map.getZoom(), 15))
    marker.openPopup()
  }
}

function focusSupply(id) {
  const marker = markers.get(`supply:${id}`)
  if (marker) {
    map.setView(marker.getLatLng(), Math.max(map.getZoom(), 15))
    marker.openPopup()
  }
}

defineExpose({ focusEmergency, focusSupply })

onBeforeUnmount(() => map?.remove())
</script>

<template>
  <div id="public-situation-map" class="situation-map" aria-label="Emergency locations map"></div>
</template>
