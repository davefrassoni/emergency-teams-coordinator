<script setup>
import { onMounted, ref } from 'vue'
import { CheckCircle2, LoaderCircle } from 'lucide-vue-next'
import BrandMark from '../components/BrandMark.vue'
import { api, appPath, saveAccess } from '../api'

const props = defineProps({ loginToken: { type: String, required: true } })
const state = ref('loading')
const error = ref('')

onMounted(async () => {
  try {
    const result = await api.confirmLogin(props.loginToken)
    saveAccess(result.situation, result.access_token, result.member)
    state.value = 'success'
    setTimeout(() => {
      window.location.href = appPath(`/operations/${result.situation.id}`)
    }, 700)
  } catch (err) {
    state.value = 'error'
    error.value = err.message
  }
})
</script>

<template>
  <main class="join-page">
    <div class="join-page__brand"><BrandMark /></div>
    <section class="join-card">
      <template v-if="state === 'loading'"><LoaderCircle class="spin" :size="29" /><h1>Signing you in…</h1></template>
      <template v-else-if="state === 'success'"><div class="join-icon"><CheckCircle2 /></div><h1>Access restored</h1><p>Opening the operation workspace.</p></template>
      <template v-else><div class="join-icon join-icon--error">!</div><h1>Link unavailable</h1><p>{{ error }}</p><a class="button button--dark" :href="appPath('/access')">Request another link</a></template>
    </section>
  </main>
</template>

