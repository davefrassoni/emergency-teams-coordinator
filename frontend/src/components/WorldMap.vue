<script setup>
import { nextTick, onBeforeUnmount, onMounted, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const props = defineProps({
  events: { type: Array, default: () => [] },
  compact: { type: Boolean, default: false },
})

const mapId = `world-events-map-${Math.random().toString(36).slice(2)}`

let map
let layerControl
const overlays = {}
const markers = new Map()

const TYPE_LABELS = {
  EARTHQUAKE: 'Earthquakes',
  CYCLONE: 'Tropical cyclones',
  FLOOD: 'Floods',
  VOLCANO: 'Volcanic activity',
  WILDFIRE: 'Wildfires',
  SEVERE_STORM: 'Severe storms',
  DROUGHT: 'Drought',
  OTHER: 'Other hazards',
}

const TYPE_CODES = {
  EARTHQUAKE: 'EQ',
  CYCLONE: 'TC',
  FLOOD: 'FL',
  VOLCANO: 'VO',
  WILDFIRE: 'WF',
  SEVERE_STORM: 'ST',
  DROUGHT: 'DR',
  OTHER: '!',
}

const ALERT_CLASS = {
  RED: 'world-event-marker--red',
  ORANGE: 'world-event-marker--orange',
  GREEN: 'world-event-marker--green',
}

function ensureOverlay(eventType) {
  if (!overlays[eventType]) {
    const group = L.layerGroup()
    overlays[eventType] = group
    layerControl.addOverlay(group, TYPE_LABELS[eventType] || eventType)
    group.addTo(map)
  }
  return overlays[eventType]
}

function markerIcon(item) {
  const modifier = ALERT_CLASS[item.alert_level] || ''
  const code = TYPE_CODES[item.event_type] || '?'
  return L.divIcon({
    className: 'map-marker-wrap',
    html: `<span class="world-event-marker ${modifier}"><i>${code}</i></span>`,
    iconSize: [26, 26],
    iconAnchor: [13, 13],
    popupAnchor: [0, -13],
  })
}

function popupContent(item) {
  const root = document.createElement('div')
  root.className = 'map-popup'
  const badge = document.createElement('span')
  badge.textContent = `${item.event_type_label} · ${item.alert_level_label}`
  const title = document.createElement('strong')
  title.textContent = item.title
  const detail = document.createElement('small')
  const parts = []
  if (item.severity_value != null) {
    parts.push(`${item.severity_value}${item.severity_unit ? ` ${item.severity_unit}` : ''}`)
  }
  if (item.country) parts.push(item.country)
  if (item.published_at) parts.push(new Date(item.published_at).toLocaleDateString())
  detail.textContent = parts.join(' · ')
  const source = document.createElement('span')
  source.className = 'world-event-source'
  source.textContent = item.source_label
  root.append(badge, title, detail, source)
  if (item.url) {
    const link = document.createElement('a')
    link.href = item.url
    link.target = '_blank'
    link.rel = 'noopener noreferrer'
    link.textContent = 'View source report'
    link.style.fontSize = '10px'
    link.style.fontWeight = '700'
    link.style.color = 'var(--primary)'
    root.append(link)
  }
  return root
}

function renderMarkers() {
  if (!map) return
  markers.forEach((marker) => marker.remove())
  markers.clear()
  props.events.forEach((item) => {
    if (item.latitude == null || item.longitude == null) return
    const point = [Number(item.latitude), Number(item.longitude)]
    if (!point.every(Number.isFinite)) return
    const target = props.compact ? map : ensureOverlay(item.event_type)
    const marker = L.marker(point, {
      icon: markerIcon(item),
      title: item.title,
      alt: `${item.event_type_label}: ${item.title}`,
      keyboard: !props.compact,
    }).addTo(target)
    if (!props.compact) marker.bindPopup(popupContent(item))
    markers.set(item.id, marker)
  })
}

onMounted(async () => {
  await nextTick()
  map = L.map(mapId, {
    zoomControl: !props.compact,
    scrollWheelZoom: !props.compact,
    dragging: !props.compact,
    attributionControl: !props.compact,
    worldCopyJump: true,
  }).setView([20, 0], 2)
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors',
  }).addTo(map)
  if (!props.compact) {
    layerControl = L.control.layers(null, {}, { collapsed: false }).addTo(map)
  }
  renderMarkers()
})

watch(() => props.events, renderMarkers, { deep: true })

function focusEvent(id) {
  const marker = markers.get(id)
  if (marker) {
    map.setView(marker.getLatLng(), Math.max(map.getZoom(), 5))
    marker.openPopup()
  }
}

defineExpose({ focusEvent })

onBeforeUnmount(() => map?.remove())
</script>

<template>
  <div :id="mapId" class="situation-map" aria-label="Global hazard events map"></div>
</template>
