<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ArrowLeft, ExternalLink, Globe2, LoaderCircle, MapPin, Radio } from 'lucide-vue-next'
import BrandMark from '../components/BrandMark.vue'
import WorldMap from '../components/WorldMap.vue'
import { api, appPath } from '../api'

const events = ref([])
const loading = ref(true)
const error = ref('')
const lastUpdated = ref(null)
const mapRef = ref(null)
let refreshTimer = null

const ALERT_ORDER = { RED: 0, ORANGE: 1, GREEN: 2, UNKNOWN: 3 }
const LEGEND_CLASS = { RED: 'legend-red', ORANGE: 'legend-orange', GREEN: 'legend-green', UNKNOWN: 'legend-gray' }

const sortedEvents = computed(() =>
  [...events.value].sort((a, b) => {
    const rank = ALERT_ORDER[a.alert_level] - ALERT_ORDER[b.alert_level]
    if (rank !== 0) return rank
    return new Date(b.published_at || 0) - new Date(a.published_at || 0)
  }),
)

async function load() {
  try {
    events.value = await api.worldEvents()
    lastUpdated.value = new Date()
    error.value = ''
  } catch (err) {
    if (!events.value.length) error.value = err.message
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  load()
  refreshTimer = setInterval(load, 60 * 60 * 1000)
})

onBeforeUnmount(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})

function openEvent(item, domEvent) {
  mapRef.value?.focusEvent(item.id)
  if (!item.url) domEvent.preventDefault()
}
</script>

<template>
  <main v-if="loading" class="loading-screen">
    <BrandMark /><LoaderCircle class="spin" :size="26" /><p>Loading global hazard events…</p>
  </main>

  <div v-else class="public-map-page">
    <header class="public-map-header">
      <BrandMark />
      <div class="public-map-title">
        <span class="status-dot"></span>
        <div><strong>Global Watch</strong><small>Earthquakes, cyclones, floods, volcanoes, wildfires &amp; storms worldwide</small></div>
      </div>
      <div class="public-live-state">
        <Radio :size="13" />
        <span>Refreshed hourly{{ lastUpdated ? ` · last update ${lastUpdated.toLocaleTimeString()}` : '' }}</span>
      </div>
      <a class="button button--soft" :href="appPath('/')"><ArrowLeft :size="16" /> Home</a>
    </header>

    <div class="public-map-layout">
      <aside class="public-sidebar">
        <div class="public-sidebar__intro">
          <span class="eyebrow"><Globe2 :size="13" /> Global disaster watch</span>
          <h1>What's happening now</h1>
          <p>Pulled from GDACS, USGS, and NASA EONET — the same class of official, key-free feeds behind sites like gdacs.org. Use the layer control on the map to show or hide hazard types.</p>
        </div>

        <p v-if="error" class="form-error" style="margin: 0 27px;">{{ error }}</p>

        <div class="world-event-list">
          <a
            v-for="item in sortedEvents"
            :key="item.id"
            :href="item.url || '#'"
            target="_blank"
            rel="noopener noreferrer"
            @click="openEvent(item, $event)"
          >
            <span
              class="map-legend"
              style="position: static; box-shadow: none; border: 0; padding: 0; background: transparent;"
            ><i :class="LEGEND_CLASS[item.alert_level]"></i></span>
            <span>
              <strong>{{ item.title }}</strong>
              <small><MapPin :size="10" /> {{ item.country || 'Location unavailable' }} · {{ item.event_type_label }}</small>
              <small v-if="item.severity_value != null">{{ item.severity_value }}{{ item.severity_unit ? ` ${item.severity_unit}` : '' }} · {{ item.source_label }}</small>
            </span>
            <ExternalLink v-if="item.url" :size="13" />
          </a>
          <div v-if="!sortedEvents.length" class="compact-empty">No active hazard events reported right now.</div>
        </div>
      </aside>

      <section class="public-map-canvas">
        <WorldMap ref="mapRef" :events="events" />
        <div class="map-legend">
          <span><i class="legend-red"></i> Red alert</span>
          <span><i class="legend-orange"></i> Orange alert</span>
          <span><i class="legend-green"></i> Green alert</span>
          <span><i class="legend-gray"></i> Unclassified</span>
        </div>
      </section>
    </div>
  </div>
</template>
