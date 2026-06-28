<script setup>
import { reactive, ref } from 'vue'
import { Heart, Lightbulb, Send, X } from 'lucide-vue-next'
import { api } from '../api'
import { useI18n } from '../i18n'

const { locale, languages, t, setLocale } = useI18n()
const open = ref(false)
const sending = ref(false)
const sent = ref(false)
const error = ref('')
const form = reactive({ contact_email: '', message: '' })

async function submit() {
  sending.value = true
  error.value = ''
  try {
    await api.requestFeature({
      ...form,
      page_url: window.location.href,
      locale: locale.value,
    })
    sent.value = true
  } catch (err) {
    error.value = err.message
  } finally {
    sending.value = false
  }
}

function close() {
  open.value = false
  setTimeout(() => { sent.value = false; error.value = ''; form.message = '' }, 200)
}
</script>

<template>
  <footer class="global-footer">
    <span>{{ t('builtBy') }} <a href="https://davefrassoni.com" target="_blank" rel="noopener">Dave Frassoni</a></span>
    <a class="donate-link" href="https://www.paypal.com/paypalme/dfranchesco" target="_blank" rel="noopener noreferrer"><Heart :size="14" /> {{ t('donate') }}</a>
    <div>
      <label class="language-control"><span>{{ t('language') }}</span><select :value="locale" @change="setLocale($event.target.value)"><option v-for="language in languages" :key="language.code" :value="language.code">{{ language.label }}</option></select></label>
      <button @click="open = true"><Lightbulb :size="14" /> {{ t('feature') }}</button>
    </div>
  </footer>

  <div v-if="open" class="modal-backdrop feature-modal" @mousedown.self="close">
    <section class="modal">
      <header class="modal__header"><div><span class="eyebrow">ReliefGrid</span><h2>{{ t('featureTitle') }}</h2></div><button class="icon-button" @click="close"><X :size="19" /></button></header>
      <div class="modal__body">
        <div v-if="sent" class="feature-sent"><Lightbulb :size="26" /><p>{{ t('sent') }}</p><button class="button button--dark" @click="close">{{ t('cancel') }}</button></div>
        <form v-else class="modal-form" @submit.prevent="submit">
          <p class="feature-help">{{ t('featureHelp') }}</p>
          <label><span>{{ t('email') }} *</span><input v-model="form.contact_email" type="email" required /></label>
          <label><span>{{ t('details') }} *</span><textarea v-model="form.message" required minlength="10" rows="6"></textarea></label>
          <p v-if="error" class="form-error">{{ error }}</p>
          <div class="modal-actions"><button type="button" class="button button--ghost" @click="close">{{ t('cancel') }}</button><button class="button button--primary" :disabled="sending">{{ sending ? '…' : t('send') }} <Send v-if="!sending" :size="16" /></button></div>
        </form>
      </div>
    </section>
  </div>
</template>
