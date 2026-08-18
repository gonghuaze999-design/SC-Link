<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import {
  cancelShare,
  createShare,
  listShares,
  listUserOptions,
  respondShare,
  type Share,
} from '../api/entities'
import { errMsg } from '../api/http'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const shares = ref<Share[]>([])
const users = ref<{ id: number; username: string; display_name: string }[]>([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    shares.value = await listShares()
  } catch (e) {
    alert(errMsg(e))
  } finally {
    loading.value = false
  }
}
onMounted(async () => {
  load()
  users.value = await listUserOptions().catch(() => [])
})

const pendingForMe = () => shares.value.filter((s) => s.status === 'pending' && s.target_id === auth.user?.id)
const activeShares = () => shares.value.filter((s) => s.status === 'active')
const history = () => shares.value.filter((s) => s.status === 'rejected' || s.status === 'cancelled')

const scopeLabels: Record<string, string> = {
  all: '全部数据',
  supplier: '上游',
  customer: '下游',
  middle: '中间层',
}
function scopeText(scopes: string[] | null) {
  if (!scopes || !scopes.length) return '—'
  if (scopes.includes('all')) return '全部数据(上游/下游/中间层)'
  return scopes.map((s) => scopeLabels[s] || s).join('、')
}
function userName(id: number) {
  return users.value.find((u) => u.id === id)?.display_name || users.value.find((u) => u.id === id)?.username || `用户#${id}`
}
function fmt(t: string | null) {
  return t ? t.replace('T', ' ').slice(0, 16) : '—'
}

// ---------- 发起申请 ----------
const dlg = reactive({ show: false })
const form = reactive({ target_id: null as number | null, scopes: ['all'] as string[], note: '' })
const formErr = ref('')

function toggleScope(s: string) {
  if (s === 'all') {
    form.scopes = form.scopes.includes('all') ? [] : ['all']
    return
  }
  form.scopes = form.scopes.filter((x) => x !== 'all')
  form.scopes = form.scopes.includes(s) ? form.scopes.filter((x) => x !== s) : [...form.scopes, s]
}

async function submit() {
  formErr.value = ''
  if (!form.target_id) {
    formErr.value = '请选择共享对象'
    return
  }
  if (!form.scopes.length) {
    formErr.value = '请选择共享范围'
    return
  }
  try {
    await createShare(form.target_id, form.scopes, form.note)
    dlg.show = false
    Object.assign(form, { target_id: null, scopes: ['all'], note: '' })
    load()
  } catch (e) {
    formErr.value = errMsg(e)
  }
}

async function respond(s: Share, action: 'approve' | 'reject') {
  try {
    await respondShare(s.id, action)
    load()
  } catch (e) {
    alert(errMsg(e))
  }
}
async function cancel(s: Share) {
  if (!window.confirm(`确认解除与 ${userName(s.target_id === auth.user?.id ? s.requester_id : s.target_id)} 的共享关系?解除后对方数据不再可见。`)) return
  try {
    await cancelShare(s.id)
    load()
  } catch (e) {
    alert(errMsg(e))
  }
}

const statusMeta: Record<string, { label: string; cls: string }> = {
  pending: { label: '待审批', cls: 'bg-amber-50 text-amber-600' },
  active: { label: '生效中', cls: 'bg-green-50 text-green-600' },
  rejected: { label: '已拒绝', cls: 'bg-red-50 text-red-600' },
  cancelled: { label: '已解除', cls: 'bg-slate-100 text-slate-500' },
}
const inputCls = 'w-full border border-line rounded-lg px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20'
const labelCls = 'block text-xs text-muted mb-1.5'
</script>

<template>
  <div class="space-y-5">
    <!-- 待处理申请 -->
    <div v-if="pendingForMe().length" class="bg-white rounded-xl border border-amber-200">
      <div class="px-4 py-3 border-b border-line text-sm font-bold text-amber-600">待我审批的共享申请</div>
      <div v-for="s in pendingForMe()" :key="s.id" class="px-4 py-3 flex items-center gap-3 border-b border-line last:border-0">
        <div class="flex-1">
          <div class="text-[13px] font-medium">{{ userName(s.requester_id) }} 申请与你共享:<b>{{ scopeText(s.scopes) }}</b></div>
          <div class="text-[11px] text-muted mt-0.5">{{ s.note ? `附言:${s.note} · ` : '' }}{{ fmt(s.requested_at) }} · 批准后共享范围内数据互相可见、共同维护</div>
        </div>
        <button class="px-4 py-2 rounded-lg text-xs bg-primary text-white" @click="respond(s, 'approve')">批准</button>
        <button class="px-4 py-2 rounded-lg text-xs border border-line text-muted" @click="respond(s, 'reject')">拒绝</button>
      </div>
    </div>

    <div class="bg-white rounded-xl border border-line">
      <div class="flex items-center px-4 py-3 border-b border-line">
        <div class="text-sm font-bold">共享管理</div>
        <button class="ml-auto px-4 py-2 rounded-lg text-xs bg-primary text-white" @click="dlg.show = true">+ 发起共享申请</button>
      </div>
      <table class="w-full text-[13px]">
        <thead>
          <tr class="text-left text-muted text-xs border-b border-line">
            <th class="px-4 py-3 font-medium">对方</th>
            <th class="px-4 py-3 font-medium">方向</th>
            <th class="px-4 py-3 font-medium">共享范围</th>
            <th class="px-4 py-3 font-medium">状态</th>
            <th class="px-4 py-3 font-medium">申请时间</th>
            <th class="px-4 py-3 font-medium">附言</th>
            <th class="px-4 py-3 font-medium text-right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading"><td colspan="7" class="px-4 py-8 text-center text-muted">加载中…</td></tr>
          <tr v-else-if="!shares.length"><td colspan="7" class="px-4 py-8 text-center text-muted">暂无共享关系,点击右上角发起申请</td></tr>
          <tr v-for="s in shares" :key="s.id" class="border-b border-line hover:bg-slate-50/60 transition">
            <td class="px-4 py-3 font-medium">{{ userName(s.requester_id === auth.user?.id ? s.target_id : s.requester_id) }}</td>
            <td class="px-4 py-3 text-muted">{{ s.requester_id === auth.user?.id ? '我发起' : '对方发起' }}</td>
            <td class="px-4 py-3 text-muted text-xs">{{ scopeText(s.scopes) }}</td>
            <td class="px-4 py-3"><span class="text-[11px] px-2 py-0.5 rounded" :class="statusMeta[s.status]?.cls">{{ statusMeta[s.status]?.label }}</span></td>
            <td class="px-4 py-3 text-muted text-xs">{{ fmt(s.requested_at) }}</td>
            <td class="px-4 py-3 text-muted text-xs max-w-[160px] truncate" :title="s.note">{{ s.note || '—' }}</td>
            <td class="px-4 py-3 text-right">
              <button v-if="s.status === 'active'" class="text-xs text-red-500 hover:underline" @click="cancel(s)">解除共享</button>
              <span v-else-if="s.status === 'pending'" class="text-xs text-muted">等待对方处理</span>
            </td>
          </tr>
        </tbody>
      </table>
      <div class="px-4 py-3 border-t border-line text-[11px] text-muted">
        共享生效后:共享范围内的数据互相可见、共同维护,每条记录标注最后维护人;申请/批准/拒绝/解除全程写入审计日志,管理员可查看全部共享关系。
      </div>
    </div>

    <!-- 发起申请弹窗 -->
    <div v-if="dlg.show" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50" @click.self="dlg.show = false">
      <div class="bg-white rounded-xl w-[440px] p-6 shadow-2xl">
        <div class="text-sm font-bold mb-4">发起数据共享申请</div>
        <div class="grid gap-3">
          <div>
            <label :class="labelCls">共享对象 *</label>
            <select v-model="form.target_id" :class="inputCls">
              <option :value="null">选择用户</option>
              <option v-for="u in users.filter((x) => x.id !== auth.user?.id)" :key="u.id" :value="u.id">{{ u.display_name || u.username }}({{ u.username }})</option>
            </select>
          </div>
          <div>
            <label :class="labelCls">共享范围 *(批准后互相可见、共同维护)</label>
            <div class="flex gap-2 flex-wrap">
              <button type="button" class="px-3 py-1.5 rounded-lg text-xs border transition" :class="form.scopes.includes('all') ? 'border-primary bg-blue-50 text-primary' : 'border-line text-muted'" @click="toggleScope('all')">全部数据</button>
              <button type="button" class="px-3 py-1.5 rounded-lg text-xs border transition" :class="form.scopes.includes('supplier') ? 'border-primary bg-blue-50 text-primary' : 'border-line text-muted'" @click="toggleScope('supplier')">上游供货方</button>
              <button type="button" class="px-3 py-1.5 rounded-lg text-xs border transition" :class="form.scopes.includes('customer') ? 'border-primary bg-blue-50 text-primary' : 'border-line text-muted'" @click="toggleScope('customer')">下游客户</button>
              <button type="button" class="px-3 py-1.5 rounded-lg text-xs border transition" :class="form.scopes.includes('middle') ? 'border-primary bg-blue-50 text-primary' : 'border-line text-muted'" @click="toggleScope('middle')">中间层</button>
            </div>
          </div>
          <div><label :class="labelCls">附言</label><input v-model="form.note" :class="inputCls" placeholder="如:一起维护 X 链路的上游资源" /></div>
        </div>
        <p v-if="formErr" class="text-xs text-red-500 mt-3">{{ formErr }}</p>
        <div class="flex justify-end gap-2 mt-5">
          <button class="px-4 py-2 rounded-lg text-xs border border-line text-muted" @click="dlg.show = false">取消</button>
          <button class="px-4 py-2 rounded-lg text-xs bg-primary text-white" @click="submit">提交申请</button>
        </div>
      </div>
    </div>
  </div>
</template>
