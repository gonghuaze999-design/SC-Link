<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()
const router = useRouter()
onMounted(async () => {
  if (auth.isLoggedIn && !auth.user) {
    await auth.loadMe()
  }
  if (auth.isLoggedIn && auth.user?.must_change_password && router.currentRoute.value.path !== '/change-password') {
    router.push('/change-password')
  }
})
</script>

<template>
  <router-view />
</template>
