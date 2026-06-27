import { ref } from 'vue'
import { api } from './api'

export function useSituationRealtime({ situationId, token = '', getVersion, onChange }) {
  const status = ref('connecting')
  let socket = null
  let stopped = true
  let reconnectTimer = null
  let pollController = null
  let polling = false
  let refreshPending = false

  function websocketUrl() {
    if (import.meta.env.VITE_WS_URL) {
      return `${import.meta.env.VITE_WS_URL.replace(/\/$/, '')}/ws/situations/${situationId}/`
    }
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const basePath = (import.meta.env.BASE_URL || '/').replace(/\/$/, '')
    return `${protocol}//${window.location.host}${basePath}/ws/situations/${situationId}/`
  }

  async function refreshOnce() {
    if (refreshPending || stopped) return
    refreshPending = true
    try {
      await onChange()
    } finally {
      refreshPending = false
    }
  }

  function scheduleReconnect() {
    clearTimeout(reconnectTimer)
    if (!stopped) reconnectTimer = setTimeout(connectSocket, 5000)
  }

  async function startPolling() {
    if (polling || stopped || socket?.readyState === WebSocket.OPEN) return
    polling = true
    status.value = 'polling'
    while (!stopped && socket?.readyState !== WebSocket.OPEN) {
      pollController = new AbortController()
      try {
        const result = await api.waitForChanges(
          situationId,
          getVersion() || 0,
          token,
          pollController.signal,
        )
        if (result.changed) await refreshOnce()
      } catch (error) {
        if (error.name !== 'AbortError' && !stopped) {
          status.value = 'offline'
          await new Promise((resolve) => setTimeout(resolve, 3000))
        }
      }
    }
    polling = false
  }

  function connectSocket() {
    if (stopped) return
    try {
      const protocols = token ? ['reliefgrid', `access.${token}`] : ['reliefgrid']
      socket = new WebSocket(websocketUrl(), protocols)
      socket.onopen = () => {
        status.value = 'websocket'
        pollController?.abort()
      }
      socket.onmessage = async (event) => {
        const message = JSON.parse(event.data)
        if (message.type === 'situation.changed' && message.version > (getVersion() || 0)) {
          await refreshOnce()
        }
      }
      socket.onerror = () => socket.close()
      socket.onclose = () => {
        if (stopped) return
        socket = null
        startPolling()
        scheduleReconnect()
      }
    } catch {
      socket = null
      startPolling()
      scheduleReconnect()
    }
  }

  function start() {
    if (!stopped) return
    stopped = false
    status.value = 'connecting'
    connectSocket()
  }

  function stop() {
    stopped = true
    clearTimeout(reconnectTimer)
    pollController?.abort()
    if (socket) {
      socket.onclose = null
      socket.close()
      socket = null
    }
  }

  return { status, start, stop }
}
