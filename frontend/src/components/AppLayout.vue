<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { changePassword } from '../api/auth'
import { errMsg } from '../api/http'
import AppLogo from './AppLogo.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

interface NavItem {
  key: string
  title: string
  path: string
  soon?: boolean
}
interface NavGroup {
  label: string
  items: NavItem[]
}

const navGroups = computed<NavGroup[]>(() => [
  {
    label: '核心业务',
    items: [
      { key: 'dashboard', title: '工作台', path: '/dashboard' },
      { key: 'board', title: '供需看板', path: '/board' },
      { key: 'match', title: '匹配中心', path: '/match' },
      { key: 'deals', title: '成本收益', path: '/deals' },
      { key: 'entities', title: '主体管理', path: '/entities' },
      { key: 'orders', title: '订单跟踪', path: '/orders' },
      { key: 'analytics', title: '分析中台', path: '/analytics' },
    ],
  },
  {
    label: '智能助手',
    items: [
      { key: 'duty', title: '值班机器人', path: '/duty' },
    ],
  },
  {
    label: '协同与设置',
    items: [
      { key: 'share', title: '共享管理', path: '/shares' },
      ...(auth.isAdmin
        ? [
            { key: 'users', title: '用户管理', path: '/users' },
            { key: 'audit', title: '审计日志', path: '/audit' },
          ]
        : []),
    ],
  },
])

const pageTitle = computed(() => (route.meta.title as string) || 'SC-Link')

const showPwd = ref(false)
const pwdForm = reactive({ old_password: '', new_password: '', confirm: '' })
const pwdError = ref('')
const pwdLoading = ref(false)

async function submitPwd() {
  pwdError.value = ''
  if (pwdForm.new_password !== pwdForm.confirm) {
    pwdError.value = '两次输入的新密码不一致'
    return
  }
  pwdLoading.value = true
  try {
    await changePassword(pwdForm.old_password, pwdForm.new_password)
    showPwd.value = false
    pwdForm.old_password = ''
    pwdForm.new_password = ''
    pwdForm.confirm = ''
  } catch (e) {
    pwdError.value = errMsg(e)
  } finally {
    pwdLoading.value = false
  }
}

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="flex h-screen">
    <aside class="w-60 bg-navy flex flex-col shrink-0">
      <div class="flex items-center gap-3.5 px-6 h-[88px] border-b border-white/10 shrink-0">
        <AppLogo :size="48" class="shrink-0 drop-shadow-lg" />
        <div>
          <div class="text-white text-lg font-bold leading-6 tracking-wide">SC-Link</div>
          <div class="text-[13px] text-slate-400 leading-4 mt-1">供应链协同中台</div>
        </div>
      </div>
      <nav class="flex-1 overflow-y-auto py-5">
        <div v-for="g in navGroups" :key="g.label" class="mb-6">
          <div class="px-6 text-xs text-slate-500 mb-2.5 tracking-widest">{{ g.label }}</div>
          <router-link
            v-for="it in g.items"
            :key="it.key"
            :to="it.path || '#'"
            :class="[
              'flex items-center gap-3 mx-2.5 px-3.5 py-2.5 rounded-lg text-sm transition',
              route.path === it.path
                ? 'bg-blue-900 text-white'
                : 'text-slate-400 hover:text-white hover:bg-white/5',
              it.soon ? 'cursor-not-allowed opacity-50' : '',
            ]"
            @click="it.soon && $event.preventDefault()"
          >
            <span
              class="w-1.5 h-1.5 rounded-full shrink-0"
              :class="route.path === it.path ? 'bg-cyan-400' : 'bg-slate-600'"
            ></span>
            {{ it.title }}
            <span
              v-if="it.soon"
              class="ml-auto text-[10px] bg-white/10 rounded px-1.5 py-0.5"
              >即将上线</span
            >
          </router-link>
        </div>
      </nav>
    </aside>

    <div class="flex-1 flex flex-col min-w-0">
      <header class="h-[72px] bg-white border-b border-line flex items-center justify-between px-8 shrink-0">
        <div class="text-lg font-semibold">{{ pageTitle }}</div>
        <div class="flex items-center gap-4">
          <span
            class="text-[13px] px-2.5 py-0.5 rounded"
            :class="auth.isAdmin ? 'bg-amber-50 text-amber-600' : 'bg-blue-50 text-blue-600'"
            >{{ auth.isAdmin ? '管理员' : '一般用户' }}</span
          >
          <span class="text-[15px] font-medium">{{ auth.user?.display_name || auth.user?.username }}</span>
          <button class="text-[13px] text-muted hover:text-primary transition" @click="showPwd = true">
            修改密码
          </button>
          <button class="text-[13px] text-muted hover:text-red-500 transition" @click="logout">
            退出登录
          </button>
        </div>
      </header>
      <main class="flex-1 overflow-y-auto p-8">
        <router-view />
      </main>
    </div>

    <div
      v-if="showPwd"
      class="fixed inset-0 bg-black/40 flex items-center justify-center z-50"
      @click.self="showPwd = false"
    >
      <div class="bg-white rounded-xl w-[360px] p-6 shadow-2xl">
        <div class="text-base font-bold mb-4">修改密码</div>
        <div class="mb-3">
          <label class="block text-[13px] text-muted mb-1.5">原密码</label>
          <input
            v-model="pwdForm.old_password"
            type="password"
            class="w-full border border-line rounded-lg px-3.5 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
        </div>
        <div class="mb-3">
          <label class="block text-[13px] text-muted mb-1.5">新密码(至少 8 位)</label>
          <input
            v-model="pwdForm.new_password"
            type="password"
            class="w-full border border-line rounded-lg px-3.5 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
        </div>
        <div class="mb-4">
          <label class="block text-[13px] text-muted mb-1.5">确认新密码</label>
          <input
            v-model="pwdForm.confirm"
            type="password"
            class="w-full border border-line rounded-lg px-3.5 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
        </div>
        <p v-if="pwdError" class="text-[13px] text-red-500 mb-3">{{ pwdError }}</p>
        <div class="flex justify-end gap-2">
          <button
            class="px-5 py-2.5 rounded-lg text-[13px] border border-line text-muted hover:bg-slate-50 transition"
            @click="showPwd = false"
          >
            取消
          </button>
          <button
            :disabled="pwdLoading"
            class="px-5 py-2.5 rounded-lg text-[13px] bg-primary disabled:opacity-60 text-white transition"
            @click="submitPwd"
          >
            确认修改
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
