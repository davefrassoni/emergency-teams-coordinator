<script setup>
import { ArrowLeft } from 'lucide-vue-next'

defineProps({
  title: { type: String, required: true },
  eyebrow: { type: String, required: true },
})
defineEmits(['back'])
</script>

<template>
  <div class="public-report-form__head">
    <button type="button" class="icon-button" @click="$emit('back')"><ArrowLeft :size="18" /></button>
    <div><span class="eyebrow">{{ eyebrow }}</span><h2>{{ title }}</h2></div>
  </div>
</template>

