<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()
onMounted(() => {
  if (auth.isLoggedIn && !auth.user) auth.loadMe()
})
</script>

<template>
  <router-view />
</template>
