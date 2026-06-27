<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ArrowRight, LoaderCircle, ShieldCheck } from 'lucide-vue-next'
import BrandMark from '../components/BrandMark.vue'
import { api, appPath, saveAccess } from '../api'

const props = defineProps({ inviteToken: { type: String, required: true } })
const info = ref(null)
const loading = ref(true)
const submitting = ref(false)
const error = ref('')
const form = reactive({ name: '', contact: '' })

onMounted(async () => {
  try {
    info.value = await api.inviteInfo(props.inviteToken)
    form.name = info.value.intended_for || ''
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
})

async function join() {
  if (!form.name.trim()) return
  error.value = ''
  submitting.value = true
  try {
    const result = await api.acceptInvite(props.inviteToken, form)
    saveAccess(result.situation, result.access_token, result.member)
    window.location.href = appPath(`/operations/${result.situation.id}`)
  } catch (err) {
    error.value = err.message
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <main class="join-page">
    <div class="join-page__brand"><BrandMark /></div>
    <section class="join-card">
      <LoaderCircle v-if="loading" class="spin" :size="28" />
      <template v-else-if="info">
        <div class="join-icon"><ShieldCheck :size="25" /></div>
        <span class="eyebrow">Secure invitation</span>
        <h1>Join the response</h1>
        <div class="join-operation">
          <strong>{{ info.situation.name }}</strong>
          <span>{{ info.situation.location }}</span>
        </div>
        <p>You’ve been invited as <strong>{{ info.role_label.toLowerCase() }}</strong>.</p>
        <form @submit.prevent="join">
          <label><span>Your name *</span><input v-model="form.name" required autofocus placeholder="Full name" /></label>
          <label><span>Phone or email</span><input v-model="form.contact" placeholder="How the team can reach you" /></label>
          <p v-if="error" class="form-error">{{ error }}</p>
          <button class="button button--primary button--full" :disabled="submitting">
            {{ submitting ? 'Joining…' : 'Join operation' }} <ArrowRight v-if="!submitting" :size="18" />
          </button>
        </form>
      </template>
      <template v-else>
        <div class="join-icon join-icon--error">!</div>
        <h1>Link unavailable</h1>
        <p>{{ error || 'This invitation could not be found.' }}</p>
        <a class="button button--dark" :href="appPath('/')">Return to ReliefGrid</a>
      </template>
    </section>
  </main>
</template>
