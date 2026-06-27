<script setup>
import { appPath } from '../api'

defineProps({ light: { type: Boolean, default: false } })
</script>

<template>
  <a class="brand" :class="{ 'brand--light': light }" :href="appPath('/')">
    <span class="brand__mark" aria-hidden="true">
      <i></i><i></i><i></i><i></i>
    </span>
    <span>ReliefGrid</span>
  </a>
</template>
