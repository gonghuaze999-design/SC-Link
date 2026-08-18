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
    class="relative min-h-screen flex items-center justify-center overflow-hidden"
    style="background: linear-gradient(160deg, #0f172a 0%, #13264f 55%, #1e3a8a 100%)"
  >
    <!-- 背景装饰 -->
    <div class="absolute -top-40 -right-32 w-[480px] h-[480px] rounded-full opacity-20" style="background: radial-gradient(circle, #06b6d4 0%, transparent 70%)"></div>
    <div class="absolute -bottom-48 -left-32 w-[560px] h-[560px] rounded-full opacity-15" style="background: radial-gradient(circle, #2563eb 0%, transparent 70%)"></div>
    <div class="absolute top-1/3 left-[12%] w-2 h-2 rounded-full bg-cyan-400/40"></div>
    <div class="absolute bottom-1/4 right-[18%] w-1.5 h-1.5 rounded-full bg-blue-400/40"></div>

    <div class="relative w-[460px] bg-white rounded-3xl shadow-2xl px-12 py-12">
      <div class="flex items-center gap-4 mb-10">
        <div class="w-14 h-14 rounded-2xl shrink-0 shadow-lg shadow-blue-500/30" style="background: linear-gradient(135deg, #2563eb, #06b6d4)"></div>
        <div>
          <div class="text-[24px] font-bold text-navy leading-7 tracking-wide">SC-Link</div>
          <div class="text-sm text-muted mt-1.5">供应链协同分析中台</div>
        </div>
      </div>
      <form @submit.prevent="submit">
        <div class="mb-6">
          <label class="block text-sm text-muted mb-2">账号</label>
          <input
            v-model="username"
            class="w-full border border-line rounded-xl px-5 py-3.5.5 text-[15px] outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition"
            placeholder="请输入账号"
          />
        </div>
        <div class="mb-8">
          <label class="block text-sm text-muted mb-2">密码</label>
          <input
            v-model="password"
            type="password"
            class="w-full border border-line rounded-xl px-5 py-3.5.5 text-[15px] outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition"
            placeholder="请输入密码"
          />
        </div>
        <p v-if="error" class="text-sm text-red-500 mb-5">{{ error }}</p>
        <button
          type="submit"
          :disabled="loading"
          class="w-full bg-primary hover:bg-primary/90 disabled:opacity-60 text-white rounded-xl py-3.5 text-[15px] font-medium transition shadow-lg shadow-blue-500/25"
        >
          {{ loading ? '登录中…' : '登 录' }}
        </button>
      </form>
      <div class="text-[13px] text-muted text-center mt-8">内部系统 · 所有操作全程留痕</div>
    </div>
  </div>
</template>
