<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import {
  AlertTriangle,
  ArrowLeft,
  Box,
  CheckCircle2,
  Clock3,
  Crosshair,
  LoaderCircle,
  MapPin,
  Navigation,
  PackageCheck,
  Plus,
  Radio,
  Send,
  ShieldCheck,
  Truck,
  UserRound,
  UsersRound,
  X,
} from 'lucide-vue-next'
import BrandMark from '../components/BrandMark.vue'
import LocationPicker from '../components/LocationPicker.vue'
import PanelHeading from '../components/PanelHeading.vue'
import SituationMap from '../components/SituationMap.vue'
import {
  api,
  appPath,
  getAccess,
  getSupplyTracking,
  saveSupplyTracking,
} from '../api'
import { useSituationRealtime } from '../realtime'
import { useI18n } from '../i18n'

const { locale, t, tl } = useI18n()

const props = defineProps({ situationId: { type: String, required: true } })
const accessToken = getAccess(props.situationId)
const data = ref(null)
const operationId = computed(() => data.value?.situation.id || props.situationId)
const loading = ref(true)
const error = ref('')
const panel = ref('browse')
const browseTab = ref('supplies')
const sending = ref(false)
const confirmation = ref('')
const formError = ref('')
const mapRef = ref(null)
const selectedPoint = ref(null)
const selectedSupply = ref(null)
const trackingEntry = ref(null)
const trackingEntries = ref(getSupplyTracking(props.situationId))
const liveTracking = ref(false)
let locationWatch = null
let lastLocationSent = 0
let locationUpdateInFlight = false

const emergencyForm = reactive({
  title: '', location: '', latitude: null, longitude: null,
  people_affected: 0, people_trapped: 0, hazards: '', details: '',
  reporter_name: '', reporter_contact: '',
})
const missingForm = reactive({
  person_name: '',
  approximate_age: null,
  physical_description: '',
  clothing: '',
  circumstances: '',
  last_seen_at: '',
  last_seen_location: '',
  latitude: null,
  longitude: null,
  reporter_name: '',
  reporter_contact: '',
})
const supplyForm = reactive({
  title: tl('Essential supplies needed'),
  delivery_location: '',
  latitude: null,
  longitude: null,
  details: '',
  requester_name: '',
  requester_contact: '',
  items: [{ name: '', quantity: 1, unit: 'UNIT' }],
})

watch(locale, () => {
  supplyForm.title = tl(supplyForm.title)
})
const pledgeForm = reactive({
  contributor_name: '',
  contributor_contact: '',
  origin_location: '',
  origin_latitude: null,
  origin_longitude: null,
  estimated_arrival: '',
  message: '',
  quantities: {},
})
const trackingForm = reactive({
  status: 'PLEDGED',
  origin_location: '',
  current_location: '',
  estimated_arrival: '',
  message: '',
})

const openEmergencies = computed(() =>
  data.value?.emergencies.filter(
    (item) => item.status !== 'RESOLVED' && !item.missing_person,
  ) || [],
)
const openMissingPeople = computed(() =>
  data.value?.emergencies.filter(
    (item) => item.status !== 'RESOLVED' && item.missing_person,
  ) || [],
)
const openSupplies = computed(() =>
  data.value?.supply_requests.filter((item) => item.status !== 'CLOSED') || [],
)
const canPublicReport = computed(() =>
  Boolean(data.value?.situation.is_public && data.value?.situation.public_reporting_enabled),
)
const selecting = computed(() => ['emergency', 'missing', 'request', 'pledge'].includes(panel.value))
const activeCommitment = computed(() => {
  if (!trackingEntry.value || !data.value) return null
  for (const request of data.value.supply_requests) {
    const commitment = request.commitments.find((item) => item.id === trackingEntry.value.id)
    if (commitment) return { ...commitment, request }
  }
  return null
})

async function load(silent = false) {
  try {
    data.value = await api.publicSituation(operationId.value, accessToken)
    if (operationId.value !== props.situationId) {
      trackingEntries.value = getSupplyTracking(operationId.value)
    }
    error.value = ''
    if (trackingEntry.value && activeCommitment.value) syncTrackingForm()
  } catch (err) {
    if (!silent) error.value = err.message
  } finally {
    loading.value = false
  }
}

const realtime = useSituationRealtime({
  situationId: () => operationId.value,
  token: accessToken,
  getVersion: () => data.value?.version || 0,
  onChange: () => load(true),
})

onMounted(async () => {
  await load()
  restoreTrackingLink()
  if (data.value) realtime.start()
})

onBeforeUnmount(() => {
  realtime.stop()
  if (locationWatch != null) navigator.geolocation.clearWatch(locationWatch)
})

function restoreTrackingLink() {
  const params = new URLSearchParams(window.location.search)
  const deliveryId = params.get('delivery')
  const trackingToken = window.location.hash.startsWith('#tracking=')
    ? window.location.hash.slice('#tracking='.length)
    : ''
  if (deliveryId && trackingToken) {
    const found = data.value?.supply_requests
      .flatMap((request) => request.commitments.map((commitment) => ({ request, commitment })))
      .find((item) => item.commitment.id === deliveryId)
    saveSupplyTracking(
      operationId.value,
      found?.commitment || { id: deliveryId, contributor_name: 'Supply contributor' },
      trackingToken,
      found?.request.title || 'Supply delivery',
    )
    trackingEntries.value = getSupplyTracking(operationId.value)
    window.history.replaceState({}, '', appPath(`/${data.value.situation.codename || `public/${operationId.value}`}`))
    openTracking(trackingEntries.value.find((item) => item.id === deliveryId))
  }
}

function resetPanel() {
  stopLiveTracking(false)
  panel.value = 'browse'
  selectedPoint.value = null
  selectedSupply.value = null
  trackingEntry.value = null
  formError.value = ''
}

function openPanel(name) {
  confirmation.value = ''
  formError.value = ''
  selectedPoint.value = null
  panel.value = name
}

function selectPoint(point) {
  selectedPoint.value = point
  formError.value = ''
  if (panel.value === 'emergency') {
    emergencyForm.latitude = point.latitude
    emergencyForm.longitude = point.longitude
  } else if (panel.value === 'missing') {
    missingForm.latitude = point.latitude
    missingForm.longitude = point.longitude
  } else if (panel.value === 'request') {
    supplyForm.latitude = point.latitude
    supplyForm.longitude = point.longitude
  } else if (panel.value === 'pledge') {
    pledgeForm.origin_latitude = point.latitude
    pledgeForm.origin_longitude = point.longitude
  }
}

function useMyLocation() {
  formError.value = ''
  if (!navigator.geolocation) {
    formError.value = 'Location is unavailable on this device.'
    return
  }
  navigator.geolocation.getCurrentPosition(
    ({ coords }) => selectPoint({
      latitude: Number(coords.latitude.toFixed(6)),
      longitude: Number(coords.longitude.toFixed(6)),
    }),
    () => { formError.value = 'We could not access your location. Tap the map instead.' },
    { enableHighAccuracy: true, timeout: 10000 },
  )
}

async function submitEmergency() {
  if (!selectedPoint.value) {
    formError.value = 'Tap the map or use your current location to place the report.'
    return
  }
  sending.value = true
  try {
    const result = await api.createPublicReport(operationId.value, emergencyForm)
    confirmation.value = result.message
    Object.assign(emergencyForm, {
      title: '', location: '', latitude: null, longitude: null,
      people_affected: 0, people_trapped: 0, hazards: '', details: '',
      reporter_name: '', reporter_contact: '',
    })
    resetPanel()
    browseTab.value = 'emergencies'
    await load(true)
  } catch (err) {
    formError.value = err.message
  } finally {
    sending.value = false
  }
}

async function submitMissingPerson() {
  if (!selectedPoint.value) {
    formError.value = 'Place the last-seen position on the map.'
    return
  }
  sending.value = true
  try {
    const body = {
      ...missingForm,
      last_seen_at: missingForm.last_seen_at
        ? new Date(missingForm.last_seen_at).toISOString()
        : null,
    }
    const result = await api.createMissingPersonReport(operationId.value, body)
    confirmation.value = result.message
    Object.assign(missingForm, {
      person_name: '', approximate_age: null, physical_description: '',
      clothing: '', circumstances: '', last_seen_at: '',
      last_seen_location: '', latitude: null, longitude: null,
      reporter_name: '', reporter_contact: '',
    })
    resetPanel()
    browseTab.value = 'missing'
    await load(true)
  } catch (err) {
    formError.value = err.message
  } finally {
    sending.value = false
  }
}

function addSupplyItem() {
  supplyForm.items.push({ name: '', quantity: 1, unit: 'UNIT' })
}

function removeSupplyItem(index) {
  if (supplyForm.items.length > 1) supplyForm.items.splice(index, 1)
}

async function submitSupplyRequest() {
  if (!selectedPoint.value) {
    formError.value = 'Place the delivery point on the map.'
    return
  }
  if (supplyForm.items.some((item) => !item.name.trim() || Number(item.quantity) <= 0)) {
    formError.value = 'Give every requested item a name and quantity.'
    return
  }
  sending.value = true
  try {
    const result = await api.createSupplyRequest(operationId.value, supplyForm)
    confirmation.value = result.message
    Object.assign(supplyForm, {
      title: 'Essential supplies needed', delivery_location: '',
      latitude: null, longitude: null, details: '', requester_name: '',
      requester_contact: '', items: [{ name: '', quantity: 1, unit: 'UNIT' }],
    })
    resetPanel()
    browseTab.value = 'supplies'
    await load(true)
  } catch (err) {
    formError.value = err.message
  } finally {
    sending.value = false
  }
}

function offerSupplies(request) {
  selectedSupply.value = request
  pledgeForm.quantities = Object.fromEntries(request.items.map((item) => [item.id, 0]))
  Object.assign(pledgeForm, {
    contributor_name: '', contributor_contact: '', origin_location: '',
    origin_latitude: null, origin_longitude: null, estimated_arrival: '', message: '',
  })
  openPanel('pledge')
  selectedSupply.value = request
}

function fillRemaining() {
  selectedSupply.value.items.forEach((item) => {
    pledgeForm.quantities[item.id] = Number(item.remaining_quantity)
  })
}

async function submitPledge() {
  const items = selectedSupply.value.items
    .map((item) => ({ item_id: item.id, quantity: Number(pledgeForm.quantities[item.id] || 0) }))
    .filter((item) => item.quantity > 0)
  if (!items.length) {
    formError.value = 'Enter the amount of at least one item you can bring.'
    return
  }
  sending.value = true
  try {
    const body = {
      contributor_name: pledgeForm.contributor_name,
      contributor_contact: pledgeForm.contributor_contact,
      origin_location: pledgeForm.origin_location,
      origin_latitude: pledgeForm.origin_latitude,
      origin_longitude: pledgeForm.origin_longitude,
      estimated_arrival: pledgeForm.estimated_arrival
        ? new Date(pledgeForm.estimated_arrival).toISOString()
        : null,
      message: pledgeForm.message,
      items,
    }
    const result = await api.createSupplyCommitment(
      operationId.value,
      selectedSupply.value.id,
      body,
    )
    saveSupplyTracking(
      operationId.value,
      result.commitment,
      result.tracking_token,
      selectedSupply.value.title,
    )
    trackingEntries.value = getSupplyTracking(operationId.value)
    await load(true)
    openTracking(trackingEntries.value.find((item) => item.id === result.commitment.id))
    confirmation.value = result.message
  } catch (err) {
    formError.value = err.message
  } finally {
    sending.value = false
  }
}

function openTracking(entry) {
  if (!entry) return
  trackingEntry.value = entry
  panel.value = 'tracking'
  selectedPoint.value = null
  formError.value = ''
  syncTrackingForm()
}

function syncTrackingForm() {
  const commitment = activeCommitment.value
  if (!commitment) return
  trackingForm.status = commitment.status
  trackingForm.origin_location = commitment.origin_location || ''
  trackingForm.current_location = commitment.current_location || ''
  trackingForm.estimated_arrival = commitment.estimated_arrival
    ? new Date(commitment.estimated_arrival).toISOString().slice(0, 16)
    : ''
  trackingForm.message = commitment.message || ''
  liveTracking.value = commitment.share_live_location
}

async function updateTracking(extra = {}) {
  if (!trackingEntry.value) return
  sending.value = true
  try {
    const body = {
      status: trackingForm.status,
      origin_location: trackingForm.origin_location,
      current_location: trackingForm.current_location,
      estimated_arrival: trackingForm.estimated_arrival
        ? new Date(trackingForm.estimated_arrival).toISOString()
        : null,
      message: trackingForm.message,
      ...extra,
    }
    await api.updateSupplyCommitment(
      operationId.value,
      trackingEntry.value.id,
      body,
      trackingEntry.value.token,
    )
    confirmation.value = 'Delivery tracking updated.'
    await load(true)
  } catch (err) {
    formError.value = err.message
  } finally {
    sending.value = false
  }
}

function startLiveTracking() {
  formError.value = ''
  if (!navigator.geolocation) {
    formError.value = 'Live location is unavailable on this device.'
    return
  }
  liveTracking.value = true
  if (trackingForm.status === 'PLEDGED') trackingForm.status = 'IN_TRANSIT'
  locationWatch = navigator.geolocation.watchPosition(
    async ({ coords }) => {
      const now = Date.now()
      if (now - lastLocationSent < 10000 || locationUpdateInFlight) return
      lastLocationSent = now
      locationUpdateInFlight = true
      try {
        await api.updateSupplyCommitment(
          operationId.value,
          trackingEntry.value.id,
          {
            status: trackingForm.status,
            current_location: 'Live GPS position',
            current_latitude: Number(coords.latitude.toFixed(6)),
            current_longitude: Number(coords.longitude.toFixed(6)),
            share_live_location: true,
          },
          trackingEntry.value.token,
        )
        await load(true)
      } catch (err) {
        formError.value = err.message
        stopLiveTracking(false)
      } finally {
        locationUpdateInFlight = false
      }
    },
    () => {
      formError.value = 'Live location permission was denied or became unavailable.'
      stopLiveTracking(false)
    },
    { enableHighAccuracy: true, maximumAge: 5000, timeout: 15000 },
  )
}

async function stopLiveTracking(updateServer = true) {
  if (locationWatch != null) {
    navigator.geolocation.clearWatch(locationWatch)
    locationWatch = null
  }
  const wasLive = liveTracking.value
  liveTracking.value = false
  if (updateServer && wasLive && trackingEntry.value) {
    await updateTracking({ share_live_location: false })
  }
}

function triageLabel(item) {
  if (item.source === 'PUBLIC' && item.status === 'REPORTED') return 'Awaiting verification'
  return item.triage_label
}

function quantity(value) {
  return Number(value).toLocaleString(locale.value, { maximumFractionDigits: 2 })
}

function formatEta(value) {
  return value ? new Date(value).toLocaleString(locale.value) : tl('Not provided')
}
</script>

<template>
  <main v-if="loading" class="loading-screen">
    <BrandMark /><LoaderCircle class="spin" :size="26" /><p>Opening the public response map…</p>
  </main>

  <main v-else-if="error" class="access-error">
    <BrandMark />
    <section>
      <div class="join-icon join-icon--error"><AlertTriangle :size="25" /></div>
      <h1>Map unavailable</h1><p>{{ error }}</p>
      <a class="button button--dark" :href="appPath('/')"><ArrowLeft :size="17" /> Back to home</a>
    </section>
  </main>

  <div v-else class="public-map-page">
    <header class="public-map-header">
      <BrandMark />
      <div class="public-map-title"><span class="status-dot"></span><div><strong>{{ data.situation.name }}</strong><small>{{ data.situation.location }}</small></div></div>
      <div class="public-live-state" :class="`public-live-state--${realtime.status.value}`"><Radio :size="13" /><span>{{ realtime.status.value === 'websocket' ? 'Live' : realtime.status.value === 'polling' ? 'Live · fallback' : 'Connecting' }}</span></div>
      <a v-if="getAccess(operationId)" class="button button--soft public-team-link" :href="appPath(`/operations/${operationId}`)"><ShieldCheck :size="16" /> Team workspace</a>
    </header>

    <div class="public-map-layout">
      <aside class="public-sidebar" :class="{ 'public-sidebar--reporting': panel !== 'browse' }">
        <template v-if="panel === 'browse'">
          <div class="public-sidebar__intro">
            <span class="eyebrow">{{ t('publicMap') }}</span>
            <h1>{{ t('needsResponse') }}</h1>
            <p>{{ canPublicReport ? 'Report an event, request essential supplies, or help fulfill a nearby request.' : 'This operation is view-only. Public reports are disabled.' }}</p>
            <div v-if="canPublicReport" class="public-primary-actions">
              <button class="button button--danger" @click="openPanel('emergency')"><AlertTriangle :size="16" /> {{ t('emergency') }}</button>
              <button class="button button--missing" @click="openPanel('missing')"><UserRound :size="16" /> {{ t('missingPerson') }}</button>
              <button class="button button--supply" @click="openPanel('request')"><Box :size="16" /> {{ t('requestSupplies') }}</button>
            </div>
          </div>

          <div v-if="confirmation" class="public-confirmation"><CheckCircle2 :size="20" /><p><strong>Update received</strong><span>{{ confirmation }}</span></p><button aria-label="Dismiss" @click="confirmation = ''"><X :size="15" /></button></div>

          <div v-if="trackingEntries.length" class="my-deliveries">
            <span><Truck :size="15" /> My supply deliveries</span>
            <button v-for="entry in trackingEntries" :key="entry.id" @click="openTracking(entry)"><strong>{{ entry.requestTitle }}</strong><small>Update ETA or location →</small></button>
          </div>

          <div class="public-browse-tabs">
            <button :class="{ active: browseTab === 'supplies' }" @click="browseTab = 'supplies'">{{ t('supplyNeeds') }} <b>{{ openSupplies.length }}</b></button>
            <button :class="{ active: browseTab === 'missing' }" @click="browseTab = 'missing'">{{ t('missingPerson') }} <b>{{ openMissingPeople.length }}</b></button>
            <button :class="{ active: browseTab === 'emergencies' }" @click="browseTab = 'emergencies'">{{ t('incidents') }} <b>{{ openEmergencies.length }}</b></button>
          </div>

          <div v-if="browseTab === 'supplies'" class="supply-list">
            <article v-for="request in openSupplies" :key="request.id" @click="mapRef?.focusSupply(request.id)">
              <header><span class="supply-icon"><Box :size="17" /></span><div><i>{{ request.status_label }}</i><h3>{{ request.title }}</h3><small><MapPin :size="11" /> {{ request.delivery_location }}</small></div></header>
              <p v-if="request.details">{{ request.details }}</p>
              <div class="supply-items">
                <div v-for="item in request.items" :key="item.id">
                  <span><strong>{{ item.name }}</strong><small>{{ quantity(item.promised_quantity) }} of {{ quantity(item.quantity) }} {{ item.unit_label }} promised</small></span>
                  <b>{{ quantity(item.remaining_quantity) }} <i>{{ item.unit_label }} left</i></b>
                  <em><i :style="{ width: `${Math.min(100, Number(item.promised_quantity) / Number(item.quantity) * 100)}%` }"></i></em>
                </div>
              </div>
              <div v-if="request.commitments.length" class="supply-enroute"><Truck :size="13" /> {{ request.commitments.length }} {{ request.commitments.length === 1 ? 'delivery' : 'deliveries' }} committed</div>
              <button v-if="canPublicReport && request.status !== 'COVERED'" class="button button--supply button--full" @click.stop="offerSupplies(request)"><PackageCheck :size="16" /> I can bring supplies</button>
              <div v-else class="supply-covered"><CheckCircle2 :size="16" /> All requested quantities are covered</div>
            </article>
            <div v-if="!openSupplies.length" class="compact-empty">No supply requests yet.</div>
          </div>

          <div v-else-if="browseTab === 'missing'" class="missing-person-list">
            <button v-for="item in openMissingPeople" :key="item.id" @click="mapRef?.focusEmergency(item.id)">
              <span class="missing-person-avatar"><UserRound :size="17" /></span>
              <span>
                <i>{{ item.status === 'REPORTED' ? 'Awaiting authority verification' : item.status_label }}</i>
                <strong>{{ item.missing_person.person_name }}</strong>
                <small><MapPin :size="12" /> Last seen: {{ item.location }}</small>
                <em v-if="item.missing_person.clothing">{{ item.missing_person.clothing }}</em>
              </span>
              <time v-if="item.missing_person.last_seen_at">{{ new Date(item.missing_person.last_seen_at).toLocaleDateString() }}</time>
            </button>
            <div v-if="!openMissingPeople.length" class="compact-empty">No missing-person reports.</div>
          </div>

          <div v-else class="public-report-list">
            <button v-for="item in openEmergencies" :key="item.id" @click="mapRef?.focusEmergency(item.id)">
              <span class="public-report-dot" :class="`public-report-dot--${item.triage.toLowerCase()}`"></span>
              <span><i>{{ triageLabel(item) }}</i><strong>{{ item.title }}</strong><small><MapPin :size="12" /> {{ item.location }}</small></span>
              <em v-if="item.people_trapped">{{ item.people_trapped }} trapped</em>
            </button>
            <div v-if="!openEmergencies.length" class="compact-empty">No open emergency reports.</div>
          </div>
        </template>

        <form v-else-if="panel === 'emergency'" class="public-report-form" @submit.prevent="submitEmergency">
          <PanelHeading title="Report an emergency" eyebrow="Public report" @back="resetPanel" />
          <div class="public-safety-note"><AlertTriangle :size="17" /><p>If you are in immediate danger, move to safety and contact local emergency services. Do not enter unstable structures.</p></div>
          <label><span>{{ t('whatHappened') }} *</span><input v-model="emergencyForm.title" required autofocus placeholder="e.g. Building collapsed" /></label>
          <label><span>{{ t('exactLocation') }} *</span><input v-model="emergencyForm.location" required placeholder="Street, building, or landmark" /></label>
          <LocationPicker :point="selectedPoint" @locate="useMyLocation" />
          <p v-if="formError" class="form-error">{{ formError }}</p>
          <div class="form-row"><label><span>{{ t('peopleAffected') }}</span><input v-model.number="emergencyForm.people_affected" type="number" min="0" /></label><label><span>{{ t('peopleTrapped') }}</span><input v-model.number="emergencyForm.people_trapped" type="number" min="0" /></label></div>
          <label><span>{{ t('hazards') }}</span><input v-model="emergencyForm.hazards" placeholder="Fire, gas, power lines…" /></label>
          <label><span>{{ t('usefulDetails') }}</span><textarea v-model="emergencyForm.details" rows="3"></textarea></label>
          <button class="button button--danger button--full" :disabled="sending">{{ sending ? '…' : t('sendReport') }} <Send v-if="!sending" :size="16" /></button>
        </form>

        <form v-else-if="panel === 'missing'" class="public-report-form" @submit.prevent="submitMissingPerson">
          <PanelHeading :title="t('reportMissing')" eyebrow="Public search report" @back="resetPanel" />
          <div class="missing-guidance"><UserRound :size="18" /><p>Place the last known position as accurately as possible. Authorities will verify this report before assigning a search team.</p></div>
          <label><span>{{ t('personName') }} *</span><input v-model="missingForm.person_name" required autofocus placeholder="Full name, or identifying label if unknown" /></label>
          <label><span>{{ t('age') }}</span><input v-model.number="missingForm.approximate_age" type="number" min="0" max="130" /></label>
          <label><span>{{ t('lastSeenLocation') }} *</span><input v-model="missingForm.last_seen_location" required placeholder="Street, shelter, station, or landmark" /></label>
          <LocationPicker :point="selectedPoint" label="Place the last-seen position on the map" @locate="useMyLocation" />
          <label><span>{{ t('lastSeenTime') }}</span><input v-model="missingForm.last_seen_at" type="datetime-local" /></label>
          <label><span>{{ t('physicalDescription') }}</span><textarea v-model="missingForm.physical_description" rows="2" placeholder="Height, hair, distinguishing features…"></textarea></label>
          <label><span>{{ t('clothing') }}</span><input v-model="missingForm.clothing" placeholder="Colors, jacket, shoes, bag…" /></label>
          <label><span>{{ t('circumstances') }}</span><textarea v-model="missingForm.circumstances" rows="2" placeholder="Where they were going, mobility or medical concerns…"></textarea></label>
          <details class="optional-fields" open><summary>{{ t('reporterContact') }}</summary><div class="public-contact-fields"><label><span>{{ t('yourName') }}</span><input v-model="missingForm.reporter_name" /></label><label><span>{{ t('email') }}</span><input v-model="missingForm.reporter_contact" /></label></div></details>
          <p v-if="formError" class="form-error">{{ formError }}</p>
          <button class="button button--missing button--full" :disabled="sending">{{ sending ? 'Sending…' : 'Send missing-person report' }} <Send v-if="!sending" :size="16" /></button>
          <small class="public-form-footnote">Reporter contact is visible only to authorized coordinators.</small>
        </form>

        <form v-else-if="panel === 'request'" class="public-report-form" @submit.prevent="submitSupplyRequest">
          <PanelHeading :title="t('requestSupplies')" eyebrow="Public supply need" @back="resetPanel" />
          <div class="supply-guidance"><Box :size="17" /><p>List exact quantities and units. Contact details help coordinators but are never shown publicly.</p></div>
          <label><span>{{ t('requestTitle') }} *</span><input v-model="supplyForm.title" required autofocus /></label>
          <label><span>{{ t('deliveryAddress') }} *</span><input v-model="supplyForm.delivery_location" required placeholder="Where supplies are needed" /></label>
          <LocationPicker :point="selectedPoint" label="Place the delivery point on the map" @locate="useMyLocation" />
          <fieldset><legend>{{ t('itemsNeeded') }}</legend><div class="supply-item-editor">
            <div v-for="(item, index) in supplyForm.items" :key="index">
              <input v-model="item.name" required placeholder="Item, e.g. Drinking water" />
              <input v-model.number="item.quantity" required type="number" min="0.01" step="0.01" aria-label="Quantity" />
              <select v-model="item.unit" aria-label="Unit"><option value="UNIT">units</option><option value="KG">kg</option><option value="LITER">liters</option><option value="BOX">boxes</option><option value="PACK">packs</option><option value="PALLET">pallets</option></select>
              <button type="button" aria-label="Remove item" @click="removeSupplyItem(index)"><X :size="15" /></button>
            </div>
            <button type="button" class="add-item-button" @click="addSupplyItem"><Plus :size="14" /> Add another item</button>
          </div></fieldset>
          <label><span>{{ t('deliveryInstructions') }}</span><textarea v-model="supplyForm.details" rows="2" placeholder="Who needs these supplies? Access details?"></textarea></label>
          <details class="optional-fields"><summary>Private requester contact</summary><div class="public-contact-fields"><label><span>Name</span><input v-model="supplyForm.requester_name" /></label><label><span>Phone</span><input v-model="supplyForm.requester_contact" /></label></div></details>
          <p v-if="formError" class="form-error">{{ formError }}</p>
          <button class="button button--supply button--full" :disabled="sending">{{ sending ? '…' : t('postSupply') }} <Send v-if="!sending" :size="16" /></button>
        </form>

        <form v-else-if="panel === 'pledge'" class="public-report-form" @submit.prevent="submitPledge">
          <PanelHeading title="Offer supplies" eyebrow="Partial or complete fulfillment" @back="resetPanel" />
          <div class="pledge-destination"><MapPin :size="17" /><span><strong>{{ selectedSupply.title }}</strong><small>Deliver to {{ selectedSupply.delivery_location }}</small></span></div>
          <fieldset><legend>What can you bring?</legend><div class="pledge-items">
            <label v-for="item in selectedSupply.items.filter((row) => Number(row.remaining_quantity) > 0)" :key="item.id">
              <span><strong>{{ item.name }}</strong><small>{{ quantity(item.remaining_quantity) }} {{ item.unit_label }} still needed</small></span>
              <input v-model.number="pledgeForm.quantities[item.id]" type="number" min="0" :max="Number(item.remaining_quantity)" step="0.01" />
              <i>{{ item.unit_label }}</i>
            </label>
            <button type="button" class="fill-remaining" @click="fillRemaining"><PackageCheck :size="14" /> Fulfill all remaining quantities</button>
          </div></fieldset>
          <label><span>Your name or organization *</span><input v-model="pledgeForm.contributor_name" required placeholder="Shown publicly with the delivery" /></label>
          <label><span>Private phone or email</span><input v-model="pledgeForm.contributor_contact" placeholder="Not shown publicly" /></label>
          <label><span>Departing from</span><input v-model="pledgeForm.origin_location" placeholder="Warehouse, neighborhood, or town" /></label>
          <LocationPicker :point="selectedPoint" label="Optionally place your origin on the map" @locate="useMyLocation" />
          <label><span>Estimated arrival</span><input v-model="pledgeForm.estimated_arrival" type="datetime-local" /></label>
          <label><span>Delivery note</span><textarea v-model="pledgeForm.message" rows="2" placeholder="Vehicle, contact instructions, constraints…"></textarea></label>
          <p v-if="formError" class="form-error">{{ formError }}</p>
          <button class="button button--supply button--full" :disabled="sending">{{ sending ? 'Reserving…' : 'Commit these supplies' }} <Truck v-if="!sending" :size="17" /></button>
          <small class="public-form-footnote">You will receive a private tracking link to update ETA, status, and location.</small>
        </form>

        <section v-else class="public-report-form tracking-panel">
          <PanelHeading title="Track my delivery" eyebrow="Private delivery controls" @back="resetPanel" />
          <template v-if="activeCommitment">
            <div v-if="confirmation" class="public-confirmation"><CheckCircle2 :size="19" /><p><strong>Saved</strong><span>{{ confirmation }}</span></p></div>
            <div class="tracking-summary"><Truck :size="22" /><div><strong>{{ activeCommitment.request.title }}</strong><span>To {{ activeCommitment.request.delivery_location }}</span></div><i>{{ activeCommitment.status_label }}</i></div>
            <div class="tracking-cargo"><span v-for="item in activeCommitment.items" :key="item.item_id"><strong>{{ quantity(item.quantity) }} {{ item.unit_label }}</strong> {{ item.name }}</span></div>
            <label><span>Delivery status</span><select v-model="trackingForm.status"><option value="PLEDGED">Preparing</option><option value="IN_TRANSIT">In transit</option><option value="ARRIVED">Arrived</option><option value="CANCELLED">Cancel commitment</option></select></label>
            <label><span>Departing from</span><input v-model="trackingForm.origin_location" /></label>
            <label><span>Estimated arrival</span><input v-model="trackingForm.estimated_arrival" type="datetime-local" /></label>
            <label><span>Current location description</span><input v-model="trackingForm.current_location" placeholder="e.g. Entering Chacao from the east" /></label>
            <label><span>Public delivery note</span><textarea v-model="trackingForm.message" rows="2"></textarea></label>
            <div class="live-tracking-card" :class="{ active: liveTracking }">
              <div><Navigation :size="20" /><span><strong>{{ liveTracking ? 'Live location is shared' : 'Share live supply location' }}</strong><small>{{ liveTracking ? 'This device updates the public map about every 10 seconds.' : 'Optional. Your precise position will be visible on the public map.' }}</small></span></div>
              <button v-if="!liveTracking" class="button button--dark" @click="startLiveTracking"><Radio :size="15" /> Start live tracking</button>
              <button v-else class="button button--ghost" @click="stopLiveTracking()"><X :size="15" /> Stop sharing</button>
            </div>
            <p v-if="activeCommitment.last_location_at" class="last-position"><Clock3 :size="13" /> Last position {{ new Date(activeCommitment.last_location_at).toLocaleString() }}</p>
            <p v-if="formError" class="form-error">{{ formError }}</p>
            <button class="button button--supply button--full" :disabled="sending || liveTracking" @click="updateTracking()">{{ sending ? 'Saving…' : 'Save delivery update' }}</button>
          </template>
          <div v-else class="compact-empty">This delivery is no longer visible. It may have been cancelled or removed.</div>
        </section>
      </aside>

      <section class="public-map-canvas">
        <div v-if="selecting" class="map-selection-banner"><Navigation :size="16" /> {{ panel === 'request' ? 'Tap the supply delivery point' : panel === 'pledge' ? 'Tap your departure point (optional)' : panel === 'missing' ? 'Tap the last-seen position' : 'Tap the emergency location' }}</div>
        <SituationMap ref="mapRef" :emergencies="data.emergencies" :supply-requests="data.supply_requests" :selecting="selecting" :selected-point="selectedPoint" @select="selectPoint" />
        <div class="map-legend"><span><i class="legend-missing"></i> Missing person</span><span><i class="legend-supply"></i> Supplies needed</span><span><i class="legend-delivery"></i> Supply delivery</span><span><i class="legend-red"></i> Emergency</span></div>
      </section>
    </div>
  </div>
</template>
