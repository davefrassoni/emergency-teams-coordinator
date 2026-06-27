<script setup>
import { computed } from 'vue'
import LandingView from './views/LandingView.vue'
import JoinView from './views/JoinView.vue'
import OperationView from './views/OperationView.vue'
import PublicMapView from './views/PublicMapView.vue'
import AccessView from './views/AccessView.vue'
import LoginConfirmView from './views/LoginConfirmView.vue'
import GlobalFooter from './components/GlobalFooter.vue'

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
  const login = path.match(/^\/login\/([^/]+)$/)
  if (login) return { name: 'login', token: login[1] }
  if (path === '/access') return { name: 'access' }
  const codename = path.match(/^\/([a-z0-9-]+)$/)
  if (codename) return { name: 'public', id: codename[1] }
  return { name: 'landing' }
})
</script>

<template>
  <JoinView v-if="route.name === 'join'" :invite-token="route.token" />
  <OperationView v-else-if="route.name === 'operation'" :situation-id="route.id" />
  <PublicMapView v-else-if="route.name === 'public'" :situation-id="route.id" />
  <AccessView v-else-if="route.name === 'access'" />
  <LoginConfirmView v-else-if="route.name === 'login'" :login-token="route.token" />
  <LandingView v-else />
  <GlobalFooter />
</template>
