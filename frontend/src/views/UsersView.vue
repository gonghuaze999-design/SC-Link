<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { createUser, listUsers, updateUser } from '../api/users'
import type { UserInfo } from '../api/auth'
import { errMsg } from '../api/http'

const users = ref<UserInfo[]>([])
const keyword = ref('')
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    users.value = await listUsers(keyword.value)
  } catch (e) {
    alert(errMsg(e))
  } finally {
    loading.value = false
  }
}
onMounted(load)

const dialog = reactive({
  show: false,
  mode: 'create' as 'create' | 'edit',
  target: null as UserInfo | null,
})
const form = reactive({
  username: '',
  display_name: '',
  role: 'user',
  password: '',
  phone: '',
  email: '',
  new_password: '',
})
const formError = ref('')

function openCreate() {
  dialog.mode = 'create'
  dialog.target = null
  Object.assign(form, {
    username: '',
    display_name: '',
    role: 'user',
    password: '',
    phone: '',
    email: '',
    new_password: '',
  })
  formError.value = ''
  dialog.show = true
}

function openEdit(u: UserInfo) {
  dialog.mode = 'edit'
  dialog.target = u
  Object.assign(form, {
    username: u.username,
    display_name: u.display_name,
    role: u.role,
    password: '',
    phone: u.phone,
    email: u.email,
    new_password: '',
  })
  formError.value = ''
  dialog.show = true
}

async function submit() {
  formError.value = ''
  try {
    if (dialog.mode === 'create') {
      await createUser({
        username: form.username,
        display_name: form.display_name,
        role: form.role,
        password: form.password,
        phone: form.phone,
        email: form.email,
      })
    } else if (dialog.target) {
      await updateUser(dialog.target.id, {
        display_name: form.display_name,
        role: form.role,
        phone: form.phone,
        email: form.email,
        new_password: form.new_password || undefined,
      })
    }
    dialog.show = false
    load()
  } catch (e) {
    formError.value = errMsg(e)
  }
}

async function toggleStatus(u: UserInfo) {
  const next = u.status === 'active' ? 'disabled' : 'active'
  const verb = next === 'disabled' ? '停用' : '启用'
  if (!window.confirm(`确认${verb}账号「${u.username}」?该操作将写入审计日志。`)) return
  try {
    await updateUser(u.id, { status: next })
    load()
  } catch (e) {
    alert(errMsg(e))
  }
}

function fmtTime(t: string | null) {
  return t ? t.replace('T', ' ').slice(0, 16) : '—'
}
</script>

<template>
  <div>
    <div class="bg-white rounded-xl border border-line">
      <div class="flex items-center gap-3 p-4 border-b border-line">
        <input
          v-model="keyword"
          class="w-64 border border-line rounded-lg px-3.5 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
          placeholder="搜索账号/姓名"
          @keyup.enter="load"
        />
        <button
          class="px-5 py-2.5 rounded-lg text-[13px] border border-line text-muted hover:bg-slate-50 transition"
          @click="load"
        >
          搜索
        </button>
        <button class="ml-auto px-5 py-2.5 rounded-lg text-[13px] bg-primary text-white transition whitespace-nowrap shrink-0" @click="openCreate">
          + 新增用户
        </button>
      </div>
      <table class="w-full text-sm">
        <thead>
          <tr class="text-left text-muted text-[13px] border-b border-line">
            <th class="px-5 py-3.5 font-medium">账号</th>
            <th class="px-5 py-3.5 font-medium">姓名</th>
            <th class="px-5 py-3.5 font-medium">角色</th>
            <th class="px-5 py-3.5 font-medium">状态</th>
            <th class="px-5 py-3.5 font-medium">电话</th>
            <th class="px-5 py-3.5 font-medium">最后登录</th>
            <th class="px-5 py-3.5 font-medium text-right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading" class="border-b border-line">
            <td colspan="7" class="px-4 py-8 text-center text-muted">加载中…</td>
          </tr>
          <tr v-else-if="!users.length" class="border-b border-line">
            <td colspan="7" class="px-4 py-8 text-center text-muted">暂无用户</td>
          </tr>
          <tr v-for="u in users" :key="u.id" class="border-b border-line hover:bg-slate-50/60 transition">
            <td class="px-5 py-3.5 font-medium">{{ u.username }}</td>
            <td class="px-5 py-3.5">{{ u.display_name || '—' }}</td>
            <td class="px-5 py-3.5">
              <span
                class="text-xs px-2 py-0.5 rounded"
                :class="u.role === 'admin' ? 'bg-amber-50 text-amber-600' : 'bg-blue-50 text-blue-600'"
                >{{ u.role === 'admin' ? '管理员' : '一般用户' }}</span
              >
            </td>
            <td class="px-5 py-3.5">
              <span
                class="text-xs px-2 py-0.5 rounded"
                :class="u.status === 'active' ? 'bg-green-50 text-green-600' : 'bg-slate-100 text-slate-500'"
                >{{ u.status === 'active' ? '正常' : '已停用' }}</span
              >
            </td>
            <td class="px-5 py-3.5 text-muted">{{ u.phone || '—' }}</td>
            <td class="px-5 py-3.5 text-muted">{{ fmtTime(u.last_login_at) }}</td>
            <td class="px-5 py-3.5 text-right whitespace-nowrap">
              <button class="text-[13px] text-primary hover:underline mr-3" @click="openEdit(u)">编辑</button>
              <button
                class="text-[13px] hover:underline"
                :class="u.status === 'active' ? 'text-red-500' : 'text-green-600'"
                @click="toggleStatus(u)"
              >
                {{ u.status === 'active' ? '停用' : '启用' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div
      v-if="dialog.show"
      class="fixed inset-0 bg-black/40 flex items-center justify-center z-50"
      @click.self="dialog.show = false"
    >
      <div class="bg-white rounded-xl w-[420px] p-6 shadow-2xl">
        <div class="text-base font-bold mb-4">
          {{ dialog.mode === 'create' ? '新增用户' : `编辑用户:${dialog.target?.username}` }}
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-[13px] text-muted mb-1.5">账号 *</label>
            <input
              v-model="form.username"
              :disabled="dialog.mode === 'edit'"
              class="w-full border border-line rounded-lg px-3.5 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 disabled:bg-slate-50 disabled:text-muted"
            />
          </div>
          <div>
            <label class="block text-[13px] text-muted mb-1.5">姓名</label>
            <input
              v-model="form.display_name"
              class="w-full border border-line rounded-lg px-3.5 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
          </div>
          <div>
            <label class="block text-[13px] text-muted mb-1.5">角色 *</label>
            <select
              v-model="form.role"
              class="w-full border border-line rounded-lg px-3.5 py-2.5 text-sm outline-none focus:border-primary bg-white"
            >
              <option value="user">一般用户</option>
              <option value="admin">管理员</option>
            </select>
          </div>
          <div>
            <label class="block text-[13px] text-muted mb-1.5">
              {{ dialog.mode === 'create' ? '初始密码 *(至少 8 位)' : '重置密码(留空则不修改)' }}
            </label>
            <input
              v-if="dialog.mode === 'create'"
              v-model="form.password"
              type="password"
              class="w-full border border-line rounded-lg px-3.5 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
            <input
              v-else
              v-model="form.new_password"
              type="password"
              placeholder="留空则不修改"
              class="w-full border border-line rounded-lg px-3.5 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
          </div>
          <div>
            <label class="block text-[13px] text-muted mb-1.5">电话</label>
            <input
              v-model="form.phone"
              class="w-full border border-line rounded-lg px-3.5 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
          </div>
          <div>
            <label class="block text-[13px] text-muted mb-1.5">邮箱</label>
            <input
              v-model="form.email"
              class="w-full border border-line rounded-lg px-3.5 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
          </div>
        </div>
        <p v-if="formError" class="text-[13px] text-red-500 mt-3">{{ formError }}</p>
        <div class="flex justify-end gap-2 mt-5">
          <button
            class="px-5 py-2.5 rounded-lg text-[13px] border border-line text-muted hover:bg-slate-50 transition"
            @click="dialog.show = false"
          >
            取消
          </button>
          <button
            class="px-5 py-2.5 rounded-lg text-[13px] bg-primary text-white transition"
            @click="submit"
          >
            {{ dialog.mode === 'create' ? '创建' : '保存' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
