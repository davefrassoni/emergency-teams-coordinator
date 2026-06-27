<script setup>
import { reactive, ref } from 'vue'
import { ArrowLeft, Mail, Send } from 'lucide-vue-next'
import BrandMark from '../components/BrandMark.vue'
import { api, appPath } from '../api'
import { useI18n } from '../i18n'

const { t } = useI18n()

const form = reactive({ codename: '', email: '' })
const sending = ref(false)
const sent = ref(false)
const error = ref('')

async function requestLink() {
  sending.value = true
  error.value = ''
  try {
    await api.requestLoginLink(form)
    sent.value = true
  } catch (err) {
    error.value = err.message
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <main class="join-page">
    <div class="join-page__brand"><BrandMark /></div>
    <section class="join-card">
      <div class="join-icon"><Mail :size="24" /></div>
      <span class="eyebrow">{{ t('passwordless') }}</span>
      <h1>{{ t('returnOperation') }}</h1>
      <template v-if="!sent">
        <p>Enter the operation codename and the administrator email used when it was created.</p>
        <form @submit.prevent="requestLink">
          <label><span>Operation codename *</span><div class="codename-field"><span>/</span><input v-model="form.codename" required autofocus placeholder="venezuela" /></div></label>
          <label><span>{{ t('adminEmail') }} *</span><input v-model="form.email" type="email" required placeholder="you@example.org" /></label>
          <p v-if="error" class="form-error">{{ error }}</p>
          <button class="button button--primary button--full" :disabled="sending">{{ sending ? '…' : t('emailLink') }} <Send v-if="!sending" :size="17" /></button>
        </form>
      </template>
      <template v-else>
        <p>Check your inbox. If this email administers the operation, the one-time link will arrive shortly.</p>
      </template>
      <a class="text-link access-back" :href="appPath('/')"><ArrowLeft :size="15" /> Back to home</a>
    </section>
  </main>
</template>
