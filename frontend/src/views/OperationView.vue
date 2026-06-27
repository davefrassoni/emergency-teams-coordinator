<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import {
  Activity as ActivityIcon,
  AlertTriangle,
  ArrowLeft,
  Building2,
  Box,
  Check,
  CheckCircle2,
  ChevronDown,
  CircleDot,
  Clock3,
  Copy,
  ExternalLink,
  Globe2,
  Mail,
  MapPin,
  Menu,
  MessageCircle,
  MoreHorizontal,
  PackageCheck,
  Plus,
  Radio,
  RefreshCw,
  Search,
  Send,
  ShieldAlert,
  UserRound,
  UsersRound,
  Truck,
  X,
} from 'lucide-vue-next'
import AppModal from '../components/AppModal.vue'
import BrandMark from '../components/BrandMark.vue'
import SituationMap from '../components/SituationMap.vue'
import { api, appPath, getAccess } from '../api'
import { useSituationRealtime } from '../realtime'
import { useI18n } from '../i18n'

const { locale, t, tl } = useI18n()
const tabLabel = (tab) => t(tab === 'incidents' ? 'incidents' : tab)

const props = defineProps({ situationId: { type: String, required: true } })
const token = getAccess(props.situationId)
const data = ref(null)
const loading = ref(true)
const refreshing = ref(false)
const fatalError = ref('')
const toast = ref('')
const activeTab = ref('map')
const operationMap = ref(null)
const mobileMenu = ref(false)
const modal = ref('')
const actionLoading = ref(false)
const lastUpdated = ref(null)
const filter = ref('OPEN')
const query = ref('')
let toastTimer

const emergencyForm = reactive({
  title: '',
  location: '',
  triage: 'UNKNOWN',
  status: 'REPORTED',
  people_affected: 0,
  people_trapped: 0,
  hazards: '',
  details: '',
  reporter_name: '',
  reporter_contact: '',
})
const teamForm = reactive({
  name: '',
  organization: '',
  specialty: 'SEARCH_RESCUE',
  status: 'AVAILABLE',
  people_count: 1,
  leader_name: '',
  contact: '',
  current_location: '',
  notes: '',
})
const inviteForm = reactive({ intended_for: '', role: 'COORDINATOR' })
const inviteResult = ref(null)

const canWrite = computed(() => data.value?.member.role !== 'VIEWER')
const isAdmin = computed(() => data.value?.member.role === 'ADMIN')
const availableTeams = computed(() => data.value?.teams.filter((team) => team.status === 'AVAILABLE') || [])
const filteredEmergencies = computed(() => {
  if (!data.value) return []
  const order = { RED: 0, YELLOW: 1, UNKNOWN: 2, GREEN: 3, BLACK: 4 }
  return data.value.emergencies
    .filter((item) => {
      if (filter.value === 'OPEN' && item.status === 'RESOLVED') return false
      if (filter.value === 'MISSING' && !item.missing_person) return false
      if (!['ALL', 'OPEN', 'MISSING'].includes(filter.value) && item.triage !== filter.value) return false
      const text = `${item.title} ${item.location}`.toLowerCase()
      return text.includes(query.value.toLowerCase())
    })
    .sort((a, b) => order[a.triage] - order[b.triage] || new Date(b.created_at) - new Date(a.created_at))
})

const triageMeta = {
  RED: { label: 'Immediate', short: 'Immediate', class: 'red' },
  YELLOW: { label: 'Urgent', short: 'Urgent', class: 'yellow' },
  GREEN: { label: 'Lower urgency', short: 'Lower', class: 'green' },
  BLACK: { label: 'Expectant / deceased', short: 'Expectant', class: 'black' },
  UNKNOWN: { label: 'Not assessed', short: 'Unassessed', class: 'gray' },
}
const statusMeta = {
  REPORTED: 'Reported',
  VERIFIED: 'Verified',
  IN_PROGRESS: 'Response underway',
  RESOLVED: 'Resolved',
}
const teamStatusMeta = {
  AVAILABLE: 'Available',
  DEPLOYED: 'Deployed',
  RESTING: 'Resting',
  UNAVAILABLE: 'Unavailable',
}

function notify(message) {
  toast.value = message
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => (toast.value = ''), 3500)
}

async function load(silent = false) {
  if (!token) {
    fatalError.value = 'This operation needs its private access link on this device.'
    loading.value = false
    return
  }
  if (silent) refreshing.value = true
  try {
    data.value = await api.dashboard(props.situationId, token)
    lastUpdated.value = new Date()
    fatalError.value = ''
  } catch (err) {
    if (!silent || [401, 403, 404].includes(err.status)) fatalError.value = err.message
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

const realtime = useSituationRealtime({
  situationId: props.situationId,
  token,
  getVersion: () => data.value?.version || 0,
  onChange: () => load(true),
})

onMounted(async () => {
  await load()
  if (data.value) realtime.start()
})
onBeforeUnmount(() => {
  realtime.stop()
  clearTimeout(toastTimer)
})

async function createEmergency() {
  actionLoading.value = true
  try {
    await api.createEmergency(props.situationId, emergencyForm, token)
    Object.assign(emergencyForm, {
      title: '', location: '', triage: 'UNKNOWN', status: 'REPORTED',
      people_affected: 0, people_trapped: 0, hazards: '', details: '',
      reporter_name: '', reporter_contact: '',
    })
    modal.value = ''
    notify('Emergency reported to the shared operation.')
    await load(true)
  } catch (err) {
    notify(err.message)
  } finally {
    actionLoading.value = false
  }
}

async function createTeam() {
  actionLoading.value = true
  try {
    await api.createTeam(props.situationId, teamForm, token)
    Object.assign(teamForm, {
      name: '', organization: '', specialty: 'SEARCH_RESCUE', status: 'AVAILABLE',
      people_count: 1, leader_name: '', contact: '', current_location: '', notes: '',
    })
    modal.value = ''
    notify('Team added and ready to coordinate.')
    await load(true)
  } catch (err) {
    notify(err.message)
  } finally {
    actionLoading.value = false
  }
}

async function updateEmergency(emergency, body) {
  try {
    await api.updateEmergency(props.situationId, emergency.id, body, token)
    notify(body.status === 'RESOLVED' ? 'Emergency marked resolved.' : 'Emergency status updated.')
    await load(true)
  } catch (err) {
    notify(err.message)
  }
}

async function updateTeam(team, status) {
  try {
    await api.updateTeam(props.situationId, team.id, { status }, token)
    notify(`${team.name} is now ${teamStatusMeta[status].toLowerCase()}.`)
    await load(true)
  } catch (err) {
    notify(err.message)
  }
}

async function assign(emergency, teamId) {
  if (!teamId) return
  try {
    await api.assignTeam(props.situationId, emergency.id, teamId, token)
    notify('Team deployed successfully.')
    await load(true)
  } catch (err) {
    notify(err.message)
  }
}

async function release(emergency, teamId) {
  try {
    await api.releaseTeam(props.situationId, emergency.id, teamId, token)
    notify('Team released and available again.')
    await load(true)
  } catch (err) {
    notify(err.message)
  }
}

async function createInvite() {
  actionLoading.value = true
  try {
    inviteResult.value = await api.createInvite(props.situationId, inviteForm, token)
  } catch (err) {
    notify(err.message)
  } finally {
    actionLoading.value = false
  }
}

async function copyInvite() {
  await navigator.clipboard.writeText(inviteResult.value.invite_url)
  notify('Invite link copied.')
}

async function nativeShare() {
  const share = {
    title: `Join ${data.value.situation.name}`,
    text: `You are invited to coordinate the ${data.value.situation.name} response.`,
    url: inviteResult.value.invite_url,
  }
  if (navigator.share) await navigator.share(share)
  else await copyInvite()
}

function openInvite() {
  inviteResult.value = null
  inviteForm.intended_for = ''
  inviteForm.role = 'COORDINATOR'
  modal.value = 'invite'
}

function relativeTime(value) {
  const minutes = Math.max(0, Math.floor((Date.now() - new Date(value)) / 60000))
  if (minutes < 1) return tl('just now')
  const formatter = new Intl.RelativeTimeFormat(locale.value, { numeric: 'always', style: 'narrow' })
  if (minutes < 60) return formatter.format(-minutes, 'minute')
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return formatter.format(-hours, 'hour')
  return formatter.format(-Math.floor(hours / 24), 'day')
}

function openMaps(location) {
  window.open(`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(location)}`, '_blank', 'noopener')
}

const publicRoute = computed(() =>
  appPath(`/${data.value?.situation.codename || `public/${props.situationId}`}`),
)
const publicMapUrl = computed(() => `${window.location.origin}${publicRoute.value}`)

async function copyPublicMap() {
  await navigator.clipboard.writeText(publicMapUrl.value)
  notify('Public map link copied.')
}

async function togglePublicReporting() {
  actionLoading.value = true
  try {
    await api.updateSituation(
      props.situationId,
      { public_reporting_enabled: !data.value.situation.public_reporting_enabled },
      token,
    )
    await load(true)
    notify(data.value.situation.public_reporting_enabled ? 'Public reporting enabled.' : 'Public reporting disabled.')
  } catch (err) {
    notify(err.message)
  } finally {
    actionLoading.value = false
  }
}
</script>

<template>
  <main v-if="loading" class="loading-screen">
    <BrandMark />
    <RefreshCw class="spin" :size="25" />
    <p>Loading the shared operation…</p>
  </main>

  <main v-else-if="fatalError" class="access-error">
    <BrandMark />
    <section>
      <div class="join-icon join-icon--error"><ShieldAlert :size="25" /></div>
      <h1>Access needed</h1>
      <p>{{ fatalError }}</p>
      <p class="muted">Ask an operation administrator for a fresh invitation, or reopen the original access link on this device.</p>
      <a class="button button--dark" :href="appPath('/')"><ArrowLeft :size="18" /> Back to home</a>
    </section>
  </main>

  <div v-else class="operation-shell">
    <header class="operation-header">
      <BrandMark />
      <div class="operation-title">
        <span class="status-dot"></span>
        <div>
          <strong>{{ data.situation.name }}</strong>
          <span><MapPin :size="13" /> {{ data.situation.location }}</span>
        </div>
      </div>
      <nav class="desktop-tabs" aria-label="Operation sections">
        <button v-for="tab in ['map', 'overview', 'incidents', 'supplies', 'teams', 'activity']" :key="tab" :class="{ active: activeTab === tab }" @click="activeTab = tab">
          {{ tabLabel(tab) }}
        </button>
      </nav>
      <div class="header-actions">
        <button class="refresh-button" :class="{ spin: refreshing }" title="Refresh" @click="load(true)"><RefreshCw :size="17" /></button>
        <button v-if="isAdmin" class="button button--soft desktop-only" @click="openInvite"><Send :size="17" /> Invite</button>
        <button v-if="isAdmin || data.situation.public_reporting_enabled" class="button button--soft desktop-only" @click="modal = 'public'"><Globe2 :size="17" /> Public map</button>
        <button v-if="canWrite" class="button button--primary desktop-only" @click="modal = 'emergency'"><Plus :size="18" /> Report emergency</button>
        <button class="user-chip desktop-only"><span>{{ data.member.name.charAt(0).toUpperCase() }}</span><i>{{ data.member.name }}<small>{{ data.member.role_label }}</small></i></button>
        <button class="icon-button mobile-only" @click="mobileMenu = !mobileMenu"><Menu v-if="!mobileMenu" /><X v-else /></button>
      </div>
      <div v-if="mobileMenu" class="mobile-menu">
        <button v-for="tab in ['map', 'overview', 'incidents', 'supplies', 'teams', 'activity']" :key="tab" @click="activeTab = tab; mobileMenu = false">
          {{ tabLabel(tab) }}
        </button>
        <button v-if="isAdmin" @click="openInvite(); mobileMenu = false">Invite coordinators</button>
        <button v-if="isAdmin || data.situation.public_reporting_enabled" @click="modal = 'public'; mobileMenu = false">Public reporting map</button>
      </div>
    </header>

    <div class="operation-content">
      <div class="context-bar">
        <div>
          <span class="live-pill live-pill--small" :class="{ 'live-pill--fallback': realtime.status.value === 'polling' }">
            <Radio :size="12" />
            {{ realtime.status.value === 'websocket' ? 'Live · WebSocket' : realtime.status.value === 'polling' ? 'Live · fallback' : 'Connecting live' }}
          </span>
          <span v-if="lastUpdated">Updated {{ relativeTime(lastUpdated) }}</span>
        </div>
        <p v-if="data.situation.description">{{ data.situation.description }}</p>
      </div>

      <template v-if="activeTab === 'map'">
        <section class="authority-map-view">
          <div class="authority-map-canvas">
            <SituationMap ref="operationMap" :emergencies="data.emergencies" :supply-requests="data.supply_requests" />
            <div class="map-legend"><span><i class="legend-missing"></i> Missing person</span><span><i class="legend-supply"></i> Supplies</span><span><i class="legend-red"></i> Emergency</span></div>
          </div>
          <aside class="authority-map-side">
            <header><span class="eyebrow">Live affected zone</span><h2>Events on the map</h2><p>{{ data.summary.open_emergencies }} emergencies · {{ data.summary.open_supply_requests }} supply needs</p></header>
            <button v-for="emergency in filteredEmergencies.slice(0, 12)" :key="emergency.id" @click="operationMap?.focusEmergency(emergency.id)">
              <span class="public-report-dot" :class="emergency.missing_person ? 'public-report-dot--missing' : `public-report-dot--${emergency.triage.toLowerCase()}`"></span>
              <span><i>{{ emergency.missing_person ? 'Missing person' : emergency.triage_label }}</i><strong>{{ emergency.title }}</strong><small>{{ emergency.location }}</small></span>
            </button>
            <button v-for="request in data.supply_requests.filter((item) => item.status !== 'CLOSED').slice(0, 8)" :key="request.id" @click="operationMap?.focusSupply(request.id)">
              <span class="public-report-dot public-report-dot--supply"></span>
              <span><i>Supply need</i><strong>{{ request.title }}</strong><small>{{ request.delivery_location }}</small></span>
            </button>
          </aside>
        </section>
      </template>

      <template v-else-if="activeTab === 'overview'">
        <section class="summary-grid">
          <article class="summary-card">
            <div class="summary-icon"><AlertTriangle :size="20" /></div>
            <div><span>Open emergencies</span><strong>{{ data.summary.open_emergencies }}</strong></div>
            <small>Needs attention</small>
          </article>
          <article class="summary-card summary-card--danger">
            <div class="summary-icon"><CircleDot :size="20" /></div>
            <div><span>Immediate</span><strong>{{ data.summary.immediate_emergencies }}</strong></div>
            <small>Red triage</small>
          </article>
          <article class="summary-card">
            <div class="summary-icon"><UsersRound :size="20" /></div>
            <div><span>People trapped</span><strong>{{ data.summary.people_trapped }}</strong></div>
            <small>Reported estimate</small>
          </article>
          <article class="summary-card summary-card--ready">
            <div class="summary-icon"><CheckCircle2 :size="20" /></div>
            <div><span>Teams available</span><strong>{{ data.summary.available_teams }}</strong></div>
            <small>{{ data.summary.total_responders }} responders total</small>
          </article>
        </section>

        <div class="dashboard-grid">
          <section class="panel incidents-panel">
            <header class="panel__header">
              <div><span class="eyebrow">Priority queue</span><h2>Active emergencies</h2></div>
              <button class="text-link" @click="activeTab = 'incidents'">View all <ExternalLink :size="15" /></button>
            </header>
            <div v-if="!filteredEmergencies.length" class="empty-state">
              <div><Check :size="25" /></div>
              <h3>No open emergencies</h3>
              <p>New reports will appear here in triage order.</p>
              <button v-if="canWrite" class="button button--soft" @click="modal = 'emergency'"><Plus :size="17" /> Report first emergency</button>
            </div>
            <div v-else class="incident-list">
              <article v-for="emergency in filteredEmergencies.slice(0, 5)" :key="emergency.id" class="incident-card" :class="`incident-card--${triageMeta[emergency.triage].class}`">
                <div class="incident-card__stripe"></div>
                <div class="incident-card__main">
                  <div class="incident-card__top">
                    <span class="tag" :class="`tag--${triageMeta[emergency.triage].class}`">{{ triageMeta[emergency.triage].label }}</span>
                    <span v-if="emergency.missing_person" class="tag tag--missing">Missing person</span>
                    <a v-if="emergency.external_source" class="tag tag--external" :href="emergency.external_source.source_url" target="_blank">External · verify</a>
                    <span class="incident-status"><i></i>{{ statusMeta[emergency.status] }}</span>
                    <time>{{ relativeTime(emergency.created_at) }}</time>
                  </div>
                  <h3>{{ emergency.title }}</h3>
                  <button class="location-link" @click="openMaps(emergency.location)"><MapPin :size="15" /> {{ emergency.location }} <ExternalLink :size="12" /></button>
                  <div v-if="emergency.missing_person" class="missing-authority-summary">
                    <UserRound :size="15" />
                    <span><strong>{{ emergency.missing_person.person_name }}<template v-if="emergency.missing_person.approximate_age"> · approx. {{ emergency.missing_person.approximate_age }}</template></strong><small>Last seen {{ emergency.missing_person.last_seen_at ? new Date(emergency.missing_person.last_seen_at).toLocaleString() : 'time unknown' }}<template v-if="emergency.missing_person.clothing"> · {{ emergency.missing_person.clothing }}</template></small></span>
                  </div>
                  <div class="incident-facts">
                    <strong v-if="emergency.people_trapped"><UsersRound :size="15" /> {{ emergency.people_trapped }} trapped</strong>
                    <span v-if="emergency.people_affected">{{ emergency.people_affected }} affected</span>
                    <span v-if="emergency.hazards"><AlertTriangle :size="14" /> {{ emergency.hazards }}</span>
                  </div>
                  <p v-if="emergency.details" class="incident-details">{{ emergency.details }}</p>
                  <div class="assigned-teams">
                    <span v-for="assignment in emergency.assignments" :key="assignment.id" class="assigned-team">
                      <UsersRound :size="14" /> {{ assignment.team_name }}
                      <button v-if="canWrite" title="Release team" @click="release(emergency, assignment.team_id)"><X :size="13" /></button>
                    </span>
                    <div v-if="canWrite && emergency.status !== 'RESOLVED'" class="assign-control">
                      <select :disabled="!availableTeams.length" aria-label="Assign available team" @change="assign(emergency, $event.target.value); $event.target.value = ''">
                        <option value="">{{ availableTeams.length ? '+ Assign team' : 'No teams available' }}</option>
                        <option v-for="team in availableTeams" :key="team.id" :value="team.id">{{ team.name }} · {{ team.specialty_label }}</option>
                      </select>
                      <ChevronDown :size="13" />
                    </div>
                  </div>
                </div>
                <div v-if="canWrite" class="incident-card__actions">
                  <select class="triage-select" :value="emergency.triage" aria-label="Set triage priority" @change="updateEmergency(emergency, { triage: $event.target.value })">
                    <option value="UNKNOWN">Set triage…</option>
                    <option value="RED">Immediate</option>
                    <option value="YELLOW">Urgent</option>
                    <option value="GREEN">Lower urgency</option>
                    <option value="BLACK">Expectant / deceased</option>
                  </select>
                  <button v-if="emergency.status === 'REPORTED'" @click="updateEmergency(emergency, { status: 'VERIFIED' })">Verify</button>
                  <button v-if="emergency.status === 'VERIFIED'" @click="updateEmergency(emergency, { status: 'IN_PROGRESS' })">Start response</button>
                  <button v-if="emergency.status !== 'RESOLVED'" class="resolve-action" @click="updateEmergency(emergency, { status: 'RESOLVED' })"><Check :size="15" /> Resolve</button>
                </div>
              </article>
            </div>
          </section>

          <aside class="dashboard-side">
            <section class="panel readiness-panel">
              <header class="panel__header">
                <div><span class="eyebrow">Resources</span><h2>Team readiness</h2></div>
                <button v-if="canWrite" class="icon-button" title="Add team" @click="modal = 'team'"><Plus :size="18" /></button>
              </header>
              <div v-if="!data.teams.length" class="compact-empty">No teams added yet.</div>
              <button v-for="team in data.teams.slice(0, 6)" :key="team.id" class="team-line" @click="activeTab = 'teams'">
                <span class="team-avatar">{{ team.name.slice(0, 2).toUpperCase() }}</span>
                <span><strong>{{ team.name }}</strong><small>{{ team.specialty_label }} · {{ team.people_count }}</small></span>
                <i :class="`team-state team-state--${team.status.toLowerCase()}`">{{ teamStatusMeta[team.status] }}</i>
              </button>
              <button v-if="data.teams.length" class="panel-footer" @click="activeTab = 'teams'">Manage all teams <ArrowLeft class="rotate-180" :size="15" /></button>
            </section>

            <section class="panel activity-panel">
              <header class="panel__header"><div><span class="eyebrow">Shared log</span><h2>Latest activity</h2></div></header>
              <div v-if="!data.activity.length" class="compact-empty">Activity will appear here.</div>
              <div v-for="item in data.activity.slice(0, 5)" :key="item.id" class="activity-line">
                <span class="activity-node"></span>
                <p>{{ item.message }}<small>{{ item.actor_name }} · {{ relativeTime(item.created_at) }}</small></p>
              </div>
              <button v-if="data.activity.length" class="panel-footer" @click="activeTab = 'activity'">View complete log <ArrowLeft class="rotate-180" :size="15" /></button>
            </section>
          </aside>
        </div>
      </template>

      <template v-else-if="activeTab === 'incidents'">
        <section class="page-heading">
          <div><span class="eyebrow">Triage & deployment</span><h1>Emergencies</h1><p>Highest urgency reports appear first.</p></div>
          <button v-if="canWrite" class="button button--primary" @click="modal = 'emergency'"><Plus :size="18" /> Report emergency</button>
        </section>
        <div class="toolbar">
          <label class="search-field"><Search :size="17" /><input v-model="query" placeholder="Search title or location" /></label>
          <div class="filter-pills">
            <button v-for="item in [{k:'OPEN',v:'Open'}, {k:'MISSING',v:`Missing (${data.summary.missing_people})`}, {k:'RED',v:'Immediate'}, {k:'YELLOW',v:'Urgent'}, {k:'ALL',v:'All'}]" :key="item.k" :class="{ active: filter === item.k }" @click="filter = item.k">{{ item.v }}</button>
          </div>
        </div>
        <section class="all-incidents">
          <article v-for="emergency in filteredEmergencies" :key="emergency.id" class="incident-card incident-card--full" :class="`incident-card--${triageMeta[emergency.triage].class}`">
            <div class="incident-card__stripe"></div>
            <div class="incident-card__main">
              <div class="incident-card__top"><span class="tag" :class="`tag--${triageMeta[emergency.triage].class}`">{{ triageMeta[emergency.triage].label }}</span><span v-if="emergency.missing_person" class="tag tag--missing">Missing person</span><a v-if="emergency.external_source" class="tag tag--external" :href="emergency.external_source.source_url" target="_blank">External · verify</a><span class="incident-status">{{ statusMeta[emergency.status] }}</span><time>{{ relativeTime(emergency.created_at) }}</time></div>
              <h3>{{ emergency.title }}</h3>
              <button class="location-link" @click="openMaps(emergency.location)"><MapPin :size="15" /> {{ emergency.location }} <ExternalLink :size="12" /></button>
              <div v-if="emergency.missing_person" class="missing-authority-summary">
                <UserRound :size="15" />
                <span><strong>{{ emergency.missing_person.person_name }}<template v-if="emergency.missing_person.approximate_age"> · approx. {{ emergency.missing_person.approximate_age }}</template></strong><small>Last seen {{ emergency.missing_person.last_seen_at ? new Date(emergency.missing_person.last_seen_at).toLocaleString() : 'time unknown' }}<template v-if="emergency.missing_person.clothing"> · {{ emergency.missing_person.clothing }}</template></small></span>
              </div>
              <div class="incident-facts"><strong v-if="emergency.people_trapped">{{ emergency.people_trapped }} trapped</strong><span>{{ emergency.people_affected }} affected</span><span v-if="emergency.hazards"><AlertTriangle :size="14" /> {{ emergency.hazards }}</span></div>
              <p v-if="emergency.details" class="incident-details">{{ emergency.details }}</p>
              <div class="assigned-teams">
                <span v-for="assignment in emergency.assignments" :key="assignment.id" class="assigned-team">{{ assignment.team_name }} <button v-if="canWrite" @click="release(emergency, assignment.team_id)"><X :size="13" /></button></span>
                <div v-if="canWrite && emergency.status !== 'RESOLVED'" class="assign-control"><select :disabled="!availableTeams.length" @change="assign(emergency, $event.target.value); $event.target.value = ''"><option value="">{{ availableTeams.length ? '+ Assign team' : 'No teams available' }}</option><option v-for="team in availableTeams" :key="team.id" :value="team.id">{{ team.name }} · {{ team.specialty_label }}</option></select><ChevronDown :size="13" /></div>
              </div>
            </div>
            <div v-if="canWrite" class="incident-card__actions">
              <select class="triage-select" :value="emergency.triage" aria-label="Set triage priority" @change="updateEmergency(emergency, { triage: $event.target.value })">
                <option value="UNKNOWN">Set triage…</option>
                <option value="RED">Immediate</option>
                <option value="YELLOW">Urgent</option>
                <option value="GREEN">Lower urgency</option>
                <option value="BLACK">Expectant / deceased</option>
              </select>
              <button v-if="emergency.status === 'REPORTED'" @click="updateEmergency(emergency, { status: 'VERIFIED' })">Verify report</button>
              <button v-if="emergency.status === 'VERIFIED'" @click="updateEmergency(emergency, { status: 'IN_PROGRESS' })">Start response</button>
              <button v-if="emergency.status !== 'RESOLVED'" class="resolve-action" @click="updateEmergency(emergency, { status: 'RESOLVED' })"><Check :size="15" /> Mark resolved</button>
            </div>
          </article>
          <div v-if="!filteredEmergencies.length" class="empty-state"><Search :size="25" /><h3>No matching emergencies</h3><p>Change the filter or report a new emergency.</p></div>
        </section>
      </template>

      <template v-else-if="activeTab === 'supplies'">
        <section class="page-heading">
          <div><span class="eyebrow">Public needs & deliveries</span><h1>Supply coordination</h1><p>{{ data.summary.open_supply_requests }} open requests, updated live.</p></div>
          <a class="button button--supply" :href="publicRoute" target="_blank"><Globe2 :size="18" /> Open supply map</a>
        </section>
        <section class="operations-supplies-grid">
          <article v-for="request in data.supply_requests.filter((item) => item.status !== 'CLOSED')" :key="request.id" class="operation-supply-card">
            <header>
              <span class="supply-icon"><PackageCheck :size="18" /></span>
              <div><span>{{ request.status_label }}</span><h3>{{ request.title }}</h3><p><MapPin :size="12" /> {{ request.delivery_location }}</p></div>
              <a :href="publicRoute" target="_blank"><ExternalLink :size="15" /></a>
            </header>
            <p v-if="request.details" class="operation-supply-details">{{ request.details }}</p>
            <div class="operation-supply-items">
              <div v-for="item in request.items" :key="item.id"><strong>{{ item.name }}</strong><span>{{ Number(item.promised_quantity).toLocaleString() }} / {{ Number(item.quantity).toLocaleString() }} {{ item.unit_label }}</span><em><i :style="{ width: `${Math.min(100, Number(item.promised_quantity) / Number(item.quantity) * 100)}%` }"></i></em></div>
            </div>
            <div v-if="request.requester_name || request.requester_contact" class="private-contact"><ShieldAlert :size="14" /><span><small>Private requester contact</small><strong>{{ request.requester_name }} {{ request.requester_contact }}</strong></span></div>
            <div class="operation-deliveries">
              <span class="field-label">Committed deliveries</span>
              <div v-for="commitment in request.commitments" :key="commitment.id">
                <Truck :size="15" />
                <span><strong>{{ commitment.contributor_name }}</strong><small>{{ commitment.status_label }} · ETA {{ commitment.estimated_arrival ? new Date(commitment.estimated_arrival).toLocaleString() : 'not provided' }}</small></span>
                <i>{{ commitment.items.map((item) => `${Number(item.quantity).toLocaleString()} ${item.unit_label} ${item.name}`).join(' · ') }}</i>
              </div>
              <p v-if="!request.commitments.length">No supplies committed yet.</p>
            </div>
          </article>
          <div v-if="!data.supply_requests.length" class="empty-state"><Box :size="25" /><h3>No supply requests</h3><p>Public supply needs will appear here in real time.</p></div>
        </section>
      </template>

      <template v-else-if="activeTab === 'teams'">
        <section class="page-heading">
          <div><span class="eyebrow">People & capabilities</span><h1>Response teams</h1><p>{{ data.summary.total_responders }} responders across {{ data.teams.length }} teams.</p></div>
          <button v-if="canWrite" class="button button--primary" @click="modal = 'team'"><Plus :size="18" /> Add team</button>
        </section>
        <section class="teams-grid">
          <article v-for="team in data.teams" :key="team.id" class="team-card">
            <header><span class="team-avatar team-avatar--large">{{ team.name.slice(0, 2).toUpperCase() }}</span><div><h3>{{ team.name }}</h3><p>{{ team.organization || team.specialty_label }}</p></div><span :class="`team-state team-state--${team.status.toLowerCase()}`">{{ teamStatusMeta[team.status] }}</span></header>
            <dl>
              <div><dt>Capability</dt><dd>{{ team.specialty_label }}</dd></div>
              <div><dt>People</dt><dd>{{ team.people_count }}</dd></div>
              <div><dt>Team lead</dt><dd>{{ team.leader_name || 'Not listed' }}</dd></div>
              <div><dt>Contact</dt><dd>{{ team.contact || 'Not listed' }}</dd></div>
            </dl>
            <div v-if="team.active_assignment" class="deployment-box"><Radio :size="16" /><span><small>Currently deployed to</small><strong>{{ team.active_assignment.emergency_title }}</strong></span></div>
            <div v-else-if="team.current_location" class="team-location"><MapPin :size="15" /> {{ team.current_location }}</div>
            <label v-if="canWrite && !team.active_assignment" class="team-status-control">Set availability<select :value="team.status" @change="updateTeam(team, $event.target.value)"><option v-for="(label, value) in teamStatusMeta" :key="value" :value="value">{{ label }}</option></select></label>
          </article>
          <button v-if="canWrite" class="add-team-card" @click="modal = 'team'"><span><Plus :size="23" /></span><strong>Add a response team</strong><small>Register capabilities and availability</small></button>
        </section>
      </template>

      <template v-else>
        <section class="page-heading">
          <div><span class="eyebrow">Accountable coordination</span><h1>Activity log</h1><p>A chronological record shared by the operation.</p></div>
        </section>
        <section class="panel full-activity">
          <div v-for="(item, index) in data.activity" :key="item.id" class="activity-record">
            <div class="activity-record__line"><span><ActivityIcon :size="16" /></span><i v-if="index !== data.activity.length - 1"></i></div>
            <div><strong>{{ item.message }}</strong><p>{{ item.actor_name || 'System' }} · {{ new Date(item.created_at).toLocaleString() }}</p></div>
          </div>
        </section>
      </template>
    </div>

    <button v-if="canWrite" class="mobile-fab" @click="modal = 'emergency'"><Plus :size="22" /> Report emergency</button>
    <transition name="toast"><div v-if="toast" class="toast"><CheckCircle2 :size="18" /> {{ toast }}</div></transition>

    <AppModal v-if="modal === 'emergency'" title="Report an emergency" eyebrow="Add to the shared priority queue" wide @close="modal = ''">
      <form class="modal-form" @submit.prevent="createEmergency">
        <div class="triage-callout"><AlertTriangle :size="18" /><p><strong>Use field protocols and qualified judgment.</strong><span>This tool records triage decisions; it does not replace clinical or structural assessment.</span></p></div>
        <div class="form-row">
          <label class="span-2"><span>What happened? *</span><input v-model="emergencyForm.title" required autofocus placeholder="e.g. Residential building partially collapsed" /></label>
          <label class="span-2"><span>Exact location or landmark *</span><input v-model="emergencyForm.location" required placeholder="Street, number, landmark, district" /></label>
        </div>
        <fieldset>
          <legend>Triage priority</legend>
          <div class="triage-options">
            <label v-for="(meta, value) in triageMeta" :key="value" :class="[`triage-option--${meta.class}`, { selected: emergencyForm.triage === value }]">
              <input v-model="emergencyForm.triage" type="radio" :value="value" /><i></i><span><strong>{{ meta.label }}</strong><small v-if="value === 'RED'">Life-threatening, act now</small><small v-else-if="value === 'YELLOW'">Serious, can briefly wait</small><small v-else-if="value === 'GREEN'">Walking wounded / minor</small><small v-else-if="value === 'BLACK'">Per local protocol</small><small v-else>Assessment still needed</small></span>
            </label>
          </div>
        </fieldset>
        <div class="form-row">
          <label><span>Estimated people affected</span><input v-model.number="emergencyForm.people_affected" type="number" min="0" /></label>
          <label><span>Estimated people trapped</span><input v-model.number="emergencyForm.people_trapped" type="number" min="0" /></label>
        </div>
        <label><span>Known hazards</span><input v-model="emergencyForm.hazards" placeholder="Gas, fire, unstable structure, electrical…" /></label>
        <label><span>Important details</span><textarea v-model="emergencyForm.details" rows="3" placeholder="Access route, building type, injuries, immediate needs…"></textarea></label>
        <details class="optional-fields"><summary>Reporter contact (optional)</summary><div class="form-row"><label><span>Reporter name</span><input v-model="emergencyForm.reporter_name" /></label><label><span>Phone or radio</span><input v-model="emergencyForm.reporter_contact" /></label></div></details>
        <div class="modal-actions"><button type="button" class="button button--ghost" @click="modal = ''">Cancel</button><button class="button button--danger" :disabled="actionLoading">{{ actionLoading ? 'Reporting…' : 'Report emergency' }} <Send v-if="!actionLoading" :size="17" /></button></div>
      </form>
    </AppModal>

    <AppModal v-if="modal === 'team'" title="Add a response team" eyebrow="Register people and capabilities" @close="modal = ''">
      <form class="modal-form" @submit.prevent="createTeam">
        <div class="form-row">
          <label><span>Team name *</span><input v-model="teamForm.name" required autofocus placeholder="e.g. Rescue Team Alpha" /></label>
          <label><span>Organization or country</span><input v-model="teamForm.organization" placeholder="e.g. Bomberos de Caracas" /></label>
        </div>
        <div class="form-row">
          <label><span>Primary capability</span><select v-model="teamForm.specialty"><option value="SEARCH_RESCUE">Search & rescue</option><option value="MEDICAL">Medical</option><option value="FIRE">Fire & hazmat</option><option value="ENGINEERING">Structural engineering</option><option value="LOGISTICS">Logistics</option><option value="SECURITY">Security</option><option value="OTHER">Other</option></select></label>
          <label><span>Number of people</span><input v-model.number="teamForm.people_count" type="number" min="1" max="999" /></label>
        </div>
        <div class="form-row">
          <label><span>Team lead</span><input v-model="teamForm.leader_name" placeholder="Full name" /></label>
          <label><span>Contact / radio</span><input v-model="teamForm.contact" placeholder="Phone, radio channel, email" /></label>
        </div>
        <label><span>Current staging location</span><input v-model="teamForm.current_location" placeholder="Base, landmark, or address" /></label>
        <label><span>Notes</span><textarea v-model="teamForm.notes" rows="2" placeholder="Equipment, languages, limitations…"></textarea></label>
        <div class="modal-actions"><button type="button" class="button button--ghost" @click="modal = ''">Cancel</button><button class="button button--primary" :disabled="actionLoading">{{ actionLoading ? 'Adding…' : 'Add team' }} <UsersRound v-if="!actionLoading" :size="17" /></button></div>
      </form>
    </AppModal>

    <AppModal v-if="modal === 'invite'" title="Invite a coordinator" eyebrow="Share secure operation access" @close="modal = ''">
      <div v-if="!inviteResult">
        <form class="modal-form" @submit.prevent="createInvite">
          <div class="invite-note"><ShieldAlert :size="19" /><p>Anyone with the generated link can use it once. It expires after 72 hours.</p></div>
          <label><span>Who is this for? (optional)</span><input v-model="inviteForm.intended_for" autofocus placeholder="Person or organization name" /></label>
          <fieldset><legend>Access level</legend><div class="role-options">
            <label :class="{ selected: inviteForm.role === 'COORDINATOR' }"><input v-model="inviteForm.role" type="radio" value="COORDINATOR" /><UserRound /><span><strong>Coordinator</strong><small>Can report, update, and deploy teams</small></span></label>
            <label :class="{ selected: inviteForm.role === 'VIEWER' }"><input v-model="inviteForm.role" type="radio" value="VIEWER" /><Search /><span><strong>Viewer</strong><small>Can see the operation but not change it</small></span></label>
            <label :class="{ selected: inviteForm.role === 'ADMIN' }"><input v-model="inviteForm.role" type="radio" value="ADMIN" /><ShieldAlert /><span><strong>Administrator</strong><small>Can also invite people and manage access</small></span></label>
          </div></fieldset>
          <div class="modal-actions"><button type="button" class="button button--ghost" @click="modal = ''">Cancel</button><button class="button button--primary" :disabled="actionLoading">{{ actionLoading ? 'Creating…' : 'Create secure link' }} <Send v-if="!actionLoading" :size="17" /></button></div>
        </form>
      </div>
      <div v-else class="share-result">
        <div class="success-mark"><Check :size="25" /></div>
        <h3>Invitation ready</h3>
        <p>Send this one-time link to {{ inviteResult.intended_for || 'the responder' }}.</p>
        <button class="copy-box" @click="copyInvite"><span>{{ inviteResult.invite_url }}</span><Copy :size="18" /></button>
        <div class="share-buttons">
          <a class="share-button share-button--whatsapp" :href="`https://wa.me/?text=${encodeURIComponent(`Join ${data.situation.name}: ${inviteResult.invite_url}`)}`" target="_blank"><MessageCircle :size="18" /> WhatsApp</a>
          <a class="share-button" :href="`mailto:?subject=${encodeURIComponent(`Join ${data.situation.name}`)}&body=${encodeURIComponent(inviteResult.invite_url)}`"><Mail :size="18" /> Email</a>
          <button class="share-button" @click="nativeShare"><MoreHorizontal :size="18" /> More</button>
        </div>
        <small>Expires {{ new Date(inviteResult.expires_at).toLocaleString() }}</small>
      </div>
    </AppModal>

    <AppModal v-if="modal === 'public'" title="Public reporting map" eyebrow="Anonymous visibility & reporting" @close="modal = ''">
      <div class="public-access-card">
        <div class="public-access-status" :class="{ enabled: data.situation.public_reporting_enabled }">
          <Globe2 :size="22" />
          <div>
            <strong>{{ data.situation.public_reporting_enabled ? 'Public map is open' : 'Public map is closed' }}</strong>
            <span v-if="data.situation.public_reporting_enabled">Anyone with this link can view event locations and submit an unverified report.</span>
            <span v-else>Only invited operation members can access information.</span>
          </div>
        </div>
        <template v-if="data.situation.public_reporting_enabled">
          <button class="copy-box" @click="copyPublicMap"><span>{{ publicMapUrl }}</span><Copy :size="18" /></button>
          <div class="public-access-actions">
            <a class="button button--primary" :href="publicRoute" target="_blank"><ExternalLink :size="16" /> Open public map</a>
            <button class="button button--soft" @click="copyPublicMap"><Copy :size="16" /> Copy link</button>
          </div>
        </template>
        <div class="access-levels">
          <h3>Access levels</h3>
          <div><span>P</span><p><strong>Public</strong><small>View the map and send unverified reports. Cannot triage or see teams.</small></p></div>
          <div><span>V</span><p><strong>Viewer</strong><small>See full operation details through a private invite.</small></p></div>
          <div><span>C</span><p><strong>Coordinator</strong><small>Verify reports, set triage, move resources, and assign teams.</small></p></div>
          <div><span>A</span><p><strong>Administrator</strong><small>Manage operation access and public reporting.</small></p></div>
        </div>
        <button v-if="isAdmin" class="button button--full" :class="data.situation.public_reporting_enabled ? 'button--ghost' : 'button--dark'" :disabled="actionLoading" @click="togglePublicReporting">
          {{ actionLoading ? 'Updating…' : data.situation.public_reporting_enabled ? 'Disable public reporting' : 'Enable public reporting' }}
        </button>
      </div>
    </AppModal>
  </div>
</template>
