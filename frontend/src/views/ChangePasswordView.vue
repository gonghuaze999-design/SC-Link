<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { changePassword } from '../api/auth'
import { errMsg } from '../api/http'
import { useAuthStore } from '../stores/auth'
import AppLogo from '../components/AppLogo.vue'

const router = useRouter()
const auth = useAuthStore()
const form = reactive({ old_password: '', new_password: '', confirm: '' })
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  if (!form.old_password) {
    error.value = '请输入原密码(管理员发放的初设密码)'
    return
  }
  if (form.new_password.length < 8) {
    error.value = '新密码至少 8 位'
    return
  }
  if (form.new_password === form.old_password) {
    error.value = '新密码不能与初设密码相同'
    return
  }
  if (form.new_password !== form.confirm) {
    error.value = '两次输入的新密码不一致'
    return
  }
  loading.value = true
  try {
    await changePassword(form.old_password, form.new_password)
    if (auth.user) auth.user.must_change_password = false
    router.push('/dashboard')
  } catch (e) {
    error.value = errMsg(e)
  } finally {
    loading.value = false
  }
}

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center" style="background: linear-gradient(160deg, #0f172a 0%, #13264f 55%, #1e3a8a 100%)">
    <div class="w-[460px] bg-white rounded-3xl shadow-2xl px-12 py-12">
      <div class="flex items-center gap-4 mb-8">
        <AppLogo :size="52" class="shrink-0" />
        <div>
          <div class="text-[20px] font-bold text-navy leading-6">设置您的登录密码</div>
          <div class="text-[13px] text-muted mt-1.5">首次登录(或密码重置后)须修改初设密码方可进入系统</div>
        </div>
      </div>
      <div class="mb-6">
        <label class="block text-[13px] text-muted mb-2">原密码(初设密码)</label>
        <input v-model="form.old_password" type="password" class="w-full h-[52px] border border-line rounded-xl px-4 text-base outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition" placeholder="请输入管理员发放的初设密码" />
      </div>
      <div class="mb-6">
        <label class="block text-[13px] text-muted mb-2">新密码(至少 8 位)</label>
        <input v-model="form.new_password" type="password" class="w-full h-[52px] border border-line rounded-xl px-4 text-base outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition" placeholder="设置新密码" />
      </div>
      <div class="mb-8">
        <label class="block text-[13px] text-muted mb-2">确认新密码</label>
        <input v-model="form.confirm" type="password" class="w-full h-[52px] border border-line rounded-xl px-4 text-base outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition" placeholder="再次输入新密码" />
      </div>
      <p v-if="error" class="text-[13px] text-red-500 mb-5">{{ error }}</p>
      <button :disabled="loading" class="w-full bg-primary hover:bg-primary/90 disabled:opacity-60 text-white rounded-xl py-3.5 text-[15px] font-medium transition shadow-lg shadow-blue-500/25" @click="submit">
        {{ loading ? '提交中…' : '设置密码并进入系统' }}
      </button>
      <div class="text-[13px] text-muted text-center mt-6">
        忘记初设密码?请联系管理员重置 · <button class="text-primary hover:underline" @click="logout">返回登录</button>
      </div>
    </div>
  </div>
</template>
