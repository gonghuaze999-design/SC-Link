<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import {
  createChain,
  deleteChain,
  listChains,
  listUserOptions,
  updateChain,
  type Chain,
} from '../../api/entities'
import { errMsg } from '../../api/http'

const rows = ref<Chain[]>([])
const userNames = ref<Record<number, string>>({})
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    rows.value = await listChains()
  } catch (e) {
    alert(errMsg(e))
  } finally {
    loading.value = false
  }
}
onMounted(async () => {
  load()
  userNames.value = Object.fromEntries((await listUserOptions().catch(() => [])).map((u) => [u.id, u.display_name || u.username]))
})

const dialog = reactive({ show: false, mode: 'create' as 'create' | 'edit', target: null as Chain | null })
const form = reactive({ name: '', region: '', contact_person: '', contact_info: '', description: '' })
const formError = ref('')

function openCreate() {
  dialog.mode = 'create'
  dialog.target = null
  Object.assign(form, { name: '', region: '', contact_person: '', contact_info: '', description: '' })
  formError.value = ''
  dialog.show = true
}
function openEdit(c: Chain) {
  dialog.mode = 'edit'
  dialog.target = c
  Object.assign(form, { name: c.name, region: c.region, contact_person: c.contact_person, contact_info: c.contact_info, description: c.description })
  formError.value = ''
  dialog.show = true
}

async function submit() {
  formError.value = ''
  try {
    if (dialog.mode === 'create') await createChain(form)
    else if (dialog.target) await updateChain(dialog.target.id, { ...form, version: dialog.target.version })
    dialog.show = false
    load()
  } catch (e) {
    formError.value = errMsg(e)
  }
}
async function remove(c: Chain) {
  if (!window.confirm(`确认删除链路方「${c.name}」?操作写入审计日志。`)) return
  try {
    await deleteChain(c.id)
    load()
  } catch (e) {
    alert(errMsg(e))
  }
}

const inputCls = 'w-full border border-line rounded-lg px-3.5 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20'
const labelCls = 'block text-[13px] text-muted mb-1.5'
function fmt(t: string | null) {
  return t ? t.replace('T', ' ').slice(0, 16) : '—'
}
</script>

<template>
  <div>
    <div class="bg-white rounded-xl border border-line">
      <div class="flex items-center p-4 border-b border-line">
        <div class="text-[13px] text-muted">同一条海外链路方下可有多个国内供货方作为代表销售设备;删除前须先解除其下供货方的关联。</div>
        <button class="ml-auto px-5 py-2.5 rounded-lg text-[13px] bg-primary text-white transition whitespace-nowrap shrink-0 shrink-0" @click="openCreate">+ 新增链路方</button>
      </div>
      <table class="w-full text-sm">
        <thead>
          <tr class="text-left text-muted text-[13px] border-b border-line">
            <th class="px-5 py-3.5 font-medium">链路方名称</th>
            <th class="px-5 py-3.5 font-medium">区域</th>
            <th class="px-5 py-3.5 font-medium">联系人</th>
            <th class="px-5 py-3.5 font-medium">联系方式</th>
            <th class="px-5 py-3.5 font-medium">背景备注</th>
            <th class="px-5 py-3.5 font-medium">维护人/更新</th>
            <th class="px-5 py-3.5 font-medium text-right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading"><td colspan="7" class="px-4 py-8 text-center text-muted">加载中…</td></tr>
          <tr v-else-if="!rows.length"><td colspan="7" class="px-4 py-8 text-center text-muted">暂无链路方,点击右上角新增</td></tr>
          <tr v-for="c in rows" :key="c.id" class="border-b border-line hover:bg-slate-50/60 transition">
            <td class="px-5 py-3.5 font-medium">{{ c.name }}</td>
            <td class="px-5 py-3.5 text-muted">{{ c.region || '—' }}</td>
            <td class="px-5 py-3.5 text-muted">{{ c.contact_person || '—' }}</td>
            <td class="px-5 py-3.5 text-muted">{{ c.contact_info || '—' }}</td>
            <td class="px-5 py-3.5 text-muted max-w-[220px] truncate" :title="c.description">{{ c.description || '—' }}</td>
            <td class="px-5 py-3.5 text-muted text-[13px]">{{ userNames[c.last_editor_id!] || '—' }}<br>{{ fmt(c.updated_at) }}</td>
            <td class="px-5 py-3.5 text-right whitespace-nowrap">
              <button class="text-[13px] text-primary hover:underline mr-3" @click="openEdit(c)">编辑</button>
              <button class="text-[13px] text-red-500 hover:underline" @click="remove(c)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="dialog.show" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50" @click.self="dialog.show = false">
      <div class="bg-white rounded-xl w-[440px] p-6 shadow-2xl">
        <div class="text-base font-bold mb-4">{{ dialog.mode === 'create' ? '新增链路方' : `编辑:${dialog.target?.name}` }}</div>
        <div class="grid gap-3">
          <div><label :class="labelCls">链路方名称 *</label><input v-model="form.name" :class="inputCls" /></div>
          <div><label :class="labelCls">区域</label><input v-model="form.region" :class="inputCls" /></div>
          <div><label :class="labelCls">联系人</label><input v-model="form.contact_person" :class="inputCls" /></div>
          <div><label :class="labelCls">联系方式</label><input v-model="form.contact_info" :class="inputCls" /></div>
          <div><label :class="labelCls">背景备注</label><textarea v-model="form.description" :class="inputCls" rows="3"></textarea></div>
        </div>
        <p v-if="formError" class="text-[13px] text-red-500 mt-3">{{ formError }}</p>
        <div class="flex justify-end gap-2 mt-5">
          <button class="px-5 py-2.5 rounded-lg text-[13px] border border-line text-muted" @click="dialog.show = false">取消</button>
          <button class="px-5 py-2.5 rounded-lg text-[13px] bg-primary text-white" @click="submit">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>
