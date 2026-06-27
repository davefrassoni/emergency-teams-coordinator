<script setup>
import { computed, reactive, ref } from 'vue'
import { ArrowRight, Building2, CheckCircle2, Radio, ShieldCheck, UsersRound } from 'lucide-vue-next'
import BrandMark from '../components/BrandMark.vue'
import { api, appPath, saveAccess } from '../api'

const form = reactive({
  name: '',
  location: '',
  description: '',
  creator_name: '',
  creator_contact: '',
})
const submitting = ref(false)
const error = ref('')
const recent = ref(JSON.parse(localStorage.getItem('reliefgrid:recent') || '[]'))
const canSubmit = computed(() => form.name.trim() && form.location.trim() && form.creator_name.trim())

async function createOperation() {
  if (!canSubmit.value || submitting.value) return
  error.value = ''
  submitting.value = true
  try {
    const result = await api.createSituation(form)
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
  <main class="landing">
    <nav class="landing-nav container">
      <BrandMark />
      <a class="text-link" href="#start">Open an operation <ArrowRight :size="16" /></a>
    </nav>

    <section class="hero container">
      <div class="hero__copy">
        <div class="live-pill"><Radio :size="14" /> Built for live response</div>
        <h1>Every team.<br /><em>One clear picture.</em></h1>
        <p class="hero__lead">
          Coordinate emergencies, triage needs, and deploy available responders from a shared,
          low-friction workspace.
        </p>
        <a class="button button--dark button--large" href="#start">
          Start coordinating <ArrowRight :size="19" />
        </a>
        <div class="trust-row">
          <span><CheckCircle2 :size="17" /> No account required</span>
          <span><ShieldCheck :size="17" /> Private access links</span>
        </div>
      </div>
      <div class="hero__visual" aria-label="Emergency coordination preview">
        <div class="signal signal--one"></div>
        <div class="signal signal--two"></div>
        <div class="visual-card">
          <div class="visual-card__top">
            <span class="mini-brand">RG</span>
            <span class="active-dot">Active response</span>
          </div>
          <p class="visual-label">Situation overview</p>
          <h3>Central District Response</h3>
          <div class="visual-stats">
            <div><strong>12</strong><span>Open cases</span></div>
            <div class="danger"><strong>4</strong><span>Immediate</span></div>
            <div><strong>7</strong><span>Teams ready</span></div>
          </div>
          <div class="visual-incident">
            <span class="triage-dot triage-dot--red"></span>
            <div><strong>Collapsed residential block</strong><small>Av. Libertador · 8 people trapped</small></div>
            <span class="tag tag--red">Immediate</span>
          </div>
          <div class="visual-incident">
            <span class="triage-dot triage-dot--yellow"></span>
            <div><strong>Medical support requested</strong><small>Plaza Bolívar · 14 affected</small></div>
            <span class="tag tag--yellow">Urgent</span>
          </div>
        </div>
      </div>
    </section>

    <section class="principles">
      <div class="container principles__grid">
        <article><Building2 /><h3>Report what matters</h3><p>Capture location, people at risk, hazards, and triage level in under a minute.</p></article>
        <article><UsersRound /><h3>Know who is ready</h3><p>See team specialties and availability before making an assignment.</p></article>
        <article><Radio /><h3>Keep one shared picture</h3><p>Status changes and deployments appear in a clear, chronological activity trail.</p></article>
      </div>
    </section>

    <section id="start" class="create-section">
      <div class="container create-grid">
        <div class="create-copy">
          <span class="eyebrow">Start in under a minute</span>
          <h2>Open a response operation</h2>
          <p>
            Anyone can start an operation. You’ll receive administrator access and can invite
            coordinators through WhatsApp, email, or any messaging app.
          </p>
          <div v-if="recent.length" class="recent-list">
            <span class="field-label">Your recent operations</span>
            <a v-for="item in recent" :key="item.id" :href="appPath(`/operations/${item.id}`)">
              <span><strong>{{ item.name }}</strong><small>{{ item.location }}</small></span>
              <ArrowRight :size="17" />
            </a>
          </div>
        </div>

        <form class="create-card" @submit.prevent="createOperation">
          <label>
            <span>Operation name *</span>
            <input v-model="form.name" required placeholder="e.g. Caracas Earthquake Response" />
          </label>
          <label>
            <span>Primary area *</span>
            <input v-model="form.location" required placeholder="City, district, or region" />
          </label>
          <label>
            <span>Brief context</span>
            <textarea v-model="form.description" rows="3" placeholder="What happened? What is the current scope?"></textarea>
          </label>
          <div class="form-row">
            <label>
              <span>Your name *</span>
              <input v-model="form.creator_name" required placeholder="Coordinator name" />
            </label>
            <label>
              <span>Contact</span>
              <input v-model="form.creator_contact" placeholder="Phone or email" />
            </label>
          </div>
          <p v-if="error" class="form-error">{{ error }}</p>
          <button class="button button--primary button--full" :disabled="!canSubmit || submitting">
            {{ submitting ? 'Opening operation…' : 'Open response operation' }}
            <ArrowRight v-if="!submitting" :size="18" />
          </button>
          <small class="form-note">You’ll be the first administrator. No password or account setup.</small>
        </form>
      </div>
    </section>
  </main>
</template>
