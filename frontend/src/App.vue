<script setup>
import { computed } from 'vue'
import LandingView from './views/LandingView.vue'
import JoinView from './views/JoinView.vue'
import OperationView from './views/OperationView.vue'
import PublicMapView from './views/PublicMapView.vue'

const basePath = (import.meta.env.BASE_URL || '/').replace(/\/$/, '')
const pathname = basePath && window.location.pathname.startsWith(basePath)
  ? window.location.pathname.slice(basePath.length)
  : window.location.pathname
const path = pathname.replace(/\/+$/, '') || '/'
const route = computed(() => {
  const join = path.match(/^\/join\/([^/]+)$/)
  if (join) return { name: 'join', token: join[1] }
  const operation = path.match(/^\/operations\/([^/]+)$/)
  if (operation) return { name: 'operation', id: operation[1] }
  const publicMap = path.match(/^\/public\/([^/]+)$/)
  if (publicMap) return { name: 'public', id: publicMap[1] }
  return { name: 'landing' }
})
</script>

<template>
  <JoinView v-if="route.name === 'join'" :invite-token="route.token" />
  <OperationView v-else-if="route.name === 'operation'" :situation-id="route.id" />
  <PublicMapView v-else-if="route.name === 'public'" :situation-id="route.id" />
  <LandingView v-else />
</template>
