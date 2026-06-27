<script setup>
import { X } from 'lucide-vue-next'

defineProps({
  title: { type: String, required: true },
  eyebrow: { type: String, default: '' },
  wide: { type: Boolean, default: false },
})
defineEmits(['close'])
</script>

<template>
  <div class="modal-backdrop" @mousedown.self="$emit('close')">
    <section class="modal" :class="{ 'modal--wide': wide }" role="dialog" aria-modal="true" :aria-label="title">
      <header class="modal__header">
        <div>
          <span v-if="eyebrow" class="eyebrow">{{ eyebrow }}</span>
          <h2>{{ title }}</h2>
        </div>
        <button class="icon-button" type="button" aria-label="Close" @click="$emit('close')">
          <X :size="20" />
        </button>
      </header>
      <div class="modal__body"><slot /></div>
    </section>
  </div>
</template>

