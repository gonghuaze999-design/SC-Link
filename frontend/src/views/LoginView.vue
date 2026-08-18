<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { errMsg } from '../api/http'

const router = useRouter()
const auth = useAuthStore()
const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

async function submit() {
  if (!username.value || !password.value) {
    error.value = '请输入账号和密码'
    return
  }
  loading.value = true
  error.value = ''
  try {
    await auth.login(username.value, password.value)
    router.push('/dashboard')
  } catch (e) {
    error.value = errMsg(e)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div
    class="min-h-screen flex items-center justify-center"
    style="background: linear-gradient(160deg, #0f172a 0%, #13264f 55%, #1e3a8a 100%)"
  >
    <div class="w-[380px] bg-white rounded-2xl shadow-2xl p-8">
      <div class="flex items-center gap-3 mb-7">
        <div
          class="w-10 h-10 rounded-xl shrink-0"
          style="background: linear-gradient(135deg, #2563eb, #06b6d4)"
        ></div>
        <div>
          <div class="text-lg font-bold text-navy leading-5">SC-Link</div>
          <div class="text-xs text-muted mt-0.5">供应链协同分析中台</div>
        </div>
      </div>
      <form @submit.prevent="submit">
        <div class="mb-4">
          <label class="block text-xs text-muted mb-1.5">账号</label>
          <input
            v-model="username"
            class="w-full border border-line rounded-lg px-3 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition"
            placeholder="请输入账号"
          />
        </div>
        <div class="mb-5">
          <label class="block text-xs text-muted mb-1.5">密码</label>
          <input
            v-model="password"
            type="password"
            class="w-full border border-line rounded-lg px-3 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition"
            placeholder="请输入密码"
          />
        </div>
        <p v-if="error" class="text-xs text-red-500 mb-3">{{ error }}</p>
        <button
          type="submit"
          :disabled="loading"
          class="w-full bg-primary hover:bg-primary/90 disabled:opacity-60 text-white rounded-lg py-2.5 text-sm font-medium transition"
        >
          {{ loading ? '登录中…' : '登 录' }}
        </button>
      </form>
    </div>
  </div>
</template>
