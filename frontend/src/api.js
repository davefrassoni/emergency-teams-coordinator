const BASE_PATH = (import.meta.env.BASE_URL || '/').replace(/\/$/, '')
const API_ROOT = import.meta.env.VITE_API_URL || `${BASE_PATH}/api`

export function appPath(path = '/') {
  const normalized = path.startsWith('/') ? path : `/${path}`
  return `${BASE_PATH}${normalized}` || '/'
}

export class ApiError extends Error {
  constructor(message, status, details) {
    super(message)
    this.status = status
    this.details = details
  }
}

async function request(path, options = {}, token = '') {
  const headers = { ...(options.headers || {}) }
  if (options.body && typeof options.body !== 'string') {
    headers['Content-Type'] = 'application/json'
    options.body = JSON.stringify(options.body)
  }
  if (token) headers.Authorization = `Bearer ${token}`

  let response
  try {
    response = await fetch(`${API_ROOT}${path}`, { ...options, headers })
  } catch (error) {
    if (error?.name === 'AbortError') throw error
    throw new ApiError('The coordination server is unreachable. Check your connection and try again.', 0)
  }

  const payload = response.status === 204 ? null : await response.json().catch(() => ({}))
  if (!response.ok) {
    const nested = payload?.details
    let message = payload?.error || 'Something went wrong.'
    if (nested && typeof nested === 'object') {
      const first = Object.values(nested).flat()[0]
      if (first) message = String(first)
    }
    throw new ApiError(message, response.status, nested)
  }
  return payload
}

export const api = {
  createSituation: (body) => request('/situations/', { method: 'POST', body }),
  requestLoginLink: (body) => request('/auth/request-link/', { method: 'POST', body }),
  confirmLogin: (token) => request(`/auth/confirm/${token}/`, { method: 'POST', body: {} }),
  requestFeature: (body) => request('/feature-requests/', { method: 'POST', body }),
  popularSituations: () => request('/situations/public/'),
  seismicEvents: () => request('/seismic-events/'),
  dashboard: (id, token) => request(`/situations/${id}/dashboard/`, {}, token),
  updateSituation: (id, body, token) =>
    request(`/situations/${id}/`, { method: 'PATCH', body }, token),
  importMissingPeople: (id, body, token) =>
    request(`/situations/${id}/imports/missing-people/`, { method: 'POST', body }, token),
  createEmergencyContact: (id, body, token) =>
    request(`/situations/${id}/contacts/`, { method: 'POST', body }, token),
  updateEmergencyContact: (id, contactId, body, token) =>
    request(`/situations/${id}/contacts/${contactId}/`, { method: 'PATCH', body }, token),
  deleteEmergencyContact: (id, contactId, token) =>
    request(`/situations/${id}/contacts/${contactId}/`, { method: 'DELETE' }, token),
  createEmergency: (id, body, token) =>
    request(`/situations/${id}/emergencies/`, { method: 'POST', body }, token),
  updateEmergency: (id, emergencyId, body, token) =>
    request(`/situations/${id}/emergencies/${emergencyId}/`, { method: 'PATCH', body }, token),
  createTeam: (id, body, token) =>
    request(`/situations/${id}/teams/`, { method: 'POST', body }, token),
  updateTeam: (id, teamId, body, token) =>
    request(`/situations/${id}/teams/${teamId}/`, { method: 'PATCH', body }, token),
  assignTeam: (id, emergencyId, teamId, token) =>
    request(
      `/situations/${id}/emergencies/${emergencyId}/assignment/`,
      { method: 'POST', body: { team_id: teamId } },
      token,
    ),
  releaseTeam: (id, emergencyId, teamId, token) =>
    request(
      `/situations/${id}/emergencies/${emergencyId}/assignment/`,
      { method: 'DELETE', body: { team_id: teamId } },
      token,
    ),
  createInvite: (id, body, token) =>
    request(`/situations/${id}/invitations/`, { method: 'POST', body }, token),
  inviteInfo: (token) => request(`/invitations/${token}/`),
  acceptInvite: (token, body) => request(`/invitations/${token}/`, { method: 'POST', body }),
  publicSituation: (id, token = '') => request(`/situations/${id}/public/`, {}, token),
  createPublicReport: (id, body) =>
    request(`/situations/${id}/public/`, { method: 'POST', body }),
  createMissingPersonReport: (id, body) =>
    request(`/situations/${id}/public/missing-people/`, { method: 'POST', body }),
  createSupplyRequest: (id, body) =>
    request(`/situations/${id}/public/supplies/`, { method: 'POST', body }),
  createSupplyCommitment: (id, supplyId, body) =>
    request(
      `/situations/${id}/public/supplies/${supplyId}/commitments/`,
      { method: 'POST', body },
    ),
  updateSupplyCommitment: (id, commitmentId, body, trackingToken) =>
    request(
      `/situations/${id}/public/commitments/${commitmentId}/`,
      {
        method: 'PATCH',
        body,
        headers: { 'X-Supply-Token': trackingToken },
      },
    ),
  waitForChanges: (id, since, token, signal) =>
    request(
      `/situations/${id}/changes/?since=${encodeURIComponent(since || 0)}&wait=25`,
      { signal },
      token,
    ),
}

export function saveAccess(situation, token, member) {
  localStorage.setItem(`reliefgrid:access:${situation.id}`, token)
  const recent = JSON.parse(localStorage.getItem('reliefgrid:recent') || '[]')
  const entry = {
    id: situation.id,
    codename: situation.codename,
    name: situation.name,
    location: situation.location,
    member: member.name,
  }
  localStorage.setItem(
    'reliefgrid:recent',
    JSON.stringify([entry, ...recent.filter((item) => item.id !== situation.id)].slice(0, 5)),
  )
}

export function getAccess(id) {
  const direct = localStorage.getItem(`reliefgrid:access:${id}`)
  if (direct) return direct
  const recent = JSON.parse(localStorage.getItem('reliefgrid:recent') || '[]')
  const operation = recent.find((item) => item.id === id || item.codename === id)
  return operation ? localStorage.getItem(`reliefgrid:access:${operation.id}`) || '' : ''
}

export function saveSupplyTracking(situationId, commitment, trackingToken, requestTitle) {
  const key = `reliefgrid:supplies:${situationId}`
  const deliveries = JSON.parse(localStorage.getItem(key) || '[]')
  const entry = {
    id: commitment.id,
    token: trackingToken,
    requestTitle,
    contributorName: commitment.contributor_name,
  }
  localStorage.setItem(
    key,
    JSON.stringify([entry, ...deliveries.filter((item) => item.id !== commitment.id)]),
  )
}

export function getSupplyTracking(situationId) {
  return JSON.parse(localStorage.getItem(`reliefgrid:supplies:${situationId}`) || '[]')
}
