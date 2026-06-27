<script setup>
import { Crosshair, MapPin } from 'lucide-vue-next'

defineProps({
  point: { type: Object, default: null },
  label: { type: String, default: 'Place this report on the map' },
})
defineEmits(['locate'])
</script>

<template>
  <div class="place-report">
    <div :class="{ placed: point }">
      <MapPin :size="20" />
      <span>
        <strong>{{ point ? 'Location placed' : label }}</strong>
        <small>{{ point ? `${point.latitude}, ${point.longitude}` : 'Tap the map at the exact location' }}</small>
      </span>
    </div>
    <button type="button" @click="$emit('locate')"><Crosshair :size="15" /> Use my location</button>
  </div>
</template>

