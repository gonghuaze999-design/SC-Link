<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { listCustomers, listSuppliers, type Customer, type Supplier } from '../api/entities'
import { listProductLines } from '../api/entities'
import {
  aiExtractTracks,
  aiOrderSummary,
  changeOrderStatus,
  createBreach,
  createOrder,
  createTrack,
  deleteOrder,
  listBreaches,
  listOrders,
  listTracks,
  ORDER_STATUSES,
  TRACK_CAT_CLS,
  updateBreach,
  updateOrder,
  type Breach,
  type Order,
  type Track,
} from '../api/orders'
import { errMsg } from '../api/http'
import { createOrderDoc, deleteOrderDoc, listOrderDocs, type OrderDoc } from '../api/deal'

const rows = ref<Order[]>([])
const suppliers = ref<Supplier[]>([])
const customers = ref<Customer[]>([])
const products = ref<{ id: number; name: string }[]>([])
const keyword = ref('')
const statusFilter = ref('')
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    rows.value = await listOrders({ keyword: keyword.value, status: statusFilter.value })
  } catch (e) {
    alert(errMsg(e))
  } finally {
    loading.value = false
  }
}
onMounted(async () => {
  load()
  suppliers.value = await listSuppliers().catch(() => [])
  customers.value = await listCustomers().catch(() => [])
  products.value = await listProductLines().catch(() => [])
})

const inputCls = 'w-full border border-line rounded-lg px-3.5 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20'
const labelCls = 'block text-[13px] text-muted mb-1.5'

// ---------- 录入订单 ----------
const dlg = reactive({ show: false, target: null as Order | null })
const form = reactive<Record<string, any>>({})
const formErr = ref('')

function blank(): Record<string, any> {
  const today = new Date().toISOString().slice(0, 10)
  return {
    order_no: `DD-${today.slice(2).replace(/-/g, '')}-${String(Math.floor(Math.random() * 900) + 100)}`,
    product_line_id: null, quantity: 0, unit_price: null, total_amount: null,
    currency: 'CNY', supplier_id: null, customer_id: null, middle_ids: [],
    payment_mode: '预付款', contract_no: '', contract_file: '', signed_at: today,
  }
}
function openCreate() {
  dlg.target = null
  Object.assign(form, blank())
  formErr.value = ''
  dlg.show = true
}
function openEdit(o: Order) {
  dlg.target = o
  const b = blank()
  for (const k of Object.keys(b)) form[k] = (o as unknown as Record<string, any>)[k] ?? b[k]
  formErr.value = ''
  dlg.show = true
}
async function submit() {
  formErr.value = ''
  if (!form.order_no) {
    formErr.value = '请填写订单编号'
    return
  }
  try {
    if (dlg.target) await updateOrder(dlg.target.id, { ...form, version: dlg.target.version })
    else await createOrder(form)
    dlg.show = false
    load()
  } catch (e) {
    formErr.value = errMsg(e)
  }
}
async function remove(o: Order) {
  if (!window.confirm(`确认删除订单「${o.order_no}」?其跟踪事件与违约事项将一并删除。`)) return
  try {
    await deleteOrder(o.id)
    load()
  } catch (e) {
    alert(errMsg(e))
  }
}

// ---------- 详情抽屉 ----------
const detail = ref<Order | null>(null)
const tracks = ref<Track[]>([])
const breaches = ref<Breach[]>([])
const aiSummary = ref('')
const aiSummaryLoading = ref(false)
const docs = ref<OrderDoc[]>([])
const docForm = reactive({ doc_type: '定稿扫描件', note: '', file: null as File | null })
const docUploading = ref(false)

async function openDetail(o: Order) {
  detail.value = o
  tracks.value = await listTracks(o.id).catch(() => [])
  breaches.value = await listBreaches(o.id).catch(() => [])
  docs.value = await listOrderDocs(o.id).catch(() => [])
  aiSummary.value = ''
}
async function uploadDoc() {
  if (!detail.value || !docForm.file) {
    alert('请选择合同文件(图片/PDF)')
    return
  }
  docUploading.value = true
  try {
    const form = new FormData()
    form.append('file', docForm.file)
    const up = await (await import('../api/entities')).uploadFile(docForm.file, 'order', detail.value.id)
    await createOrderDoc(detail.value.id, { doc_type: docForm.doc_type, file_name: up.original_name, file_path: up.stored_name, note: docForm.note })
    docs.value = await listOrderDocs(detail.value.id)
    docForm.note = ''
    docForm.file = null
  } catch (e) {
    alert(errMsg(e))
  } finally {
    docUploading.value = false
  }
}
async function removeDoc(d: OrderDoc) {
  if (!window.confirm(`删除合同文件「${d.file_name}」?`)) return
  try {
    await deleteOrderDoc(d.id)
    docs.value = await listOrderDocs(detail.value!.id)
  } catch (e) {
    alert(errMsg(e))
  }
}
function onDocPicked(e: Event) {
  docForm.file = (e.target as HTMLInputElement).files?.[0] || null
}
async function doAiSummary() {
  if (!detail.value) return
  aiSummaryLoading.value = true
  try {
    aiSummary.value = await aiOrderSummary(detail.value.id)
  } catch (e) {
    alert(errMsg(e))
  } finally {
    aiSummaryLoading.value = false
  }
}

const flowSteps = ['registered', 'sourcing', 'sourced', 'paying', 'paid', 'arrived', 'delivered', 'done']
const flowIdx = (s: string) => {
  const i = flowSteps.indexOf(s)
  return i >= 0 ? i : -1
}
async function advance(o: Order) {
  if (!detail.value) return
  try {
    const next = flowSteps[flowIdx(o.status) + 1]
    if (!next) return
    detail.value = await changeOrderStatus(o.id, next)
    await openDetail(detail.value)
    load()
  } catch (e) {
    alert(errMsg(e))
  }
}
async function toBreach(o: Order) {
  if (!window.confirm('确认标记该订单为违约?将记录当前环节,解决后自动回到该环节。')) return
  if (!detail.value) return
  try {
    await changeOrderStatus(o.id, 'breach')
    alert('已标记违约,请到违约处理中推进:补充违约事项并跟踪履约')
    detail.value = null
    load()
  } catch (e) {
    alert(errMsg(e))
  }
}
async function resolveBreach(o: Order) {
  if (!detail.value) return
  try {
    detail.value = await changeOrderStatus(o.id, 'breach_resolved')
    alert('违约已解决,订单回到违约前环节')
    await openDetail(detail.value)
    load()
  } catch (e) {
    alert(errMsg(e))
  }
}

// ---------- 跟踪事件 ----------
const trackDlg = reactive({ show: false })
const trackForm = reactive({ category: '其他', title: '', content: '' })
const trackErr = ref('')
async function saveTrack() {
  trackErr.value = ''
  if (!trackForm.content.trim()) {
    trackErr.value = '请填写事件内容'
    return
  }
  if (!detail.value) return
  try {
    await createTrack(detail.value.id, { ...trackForm })
    trackDlg.show = false
    Object.assign(trackForm, { category: '其他', title: '', content: '' })
    tracks.value = await listTracks(detail.value.id)
  } catch (e) {
    trackErr.value = errMsg(e)
  }
}

// ---------- AI 提取 ----------
const aiDlg = reactive({ show: false })
const aiText = ref('')
const aiEvents = ref<{ category: string; title: string; content: string; next_action: string }[]>([])
const aiLoading = ref(false)
const aiErr = ref('')
async function doAiExtract() {
  aiErr.value = ''
  aiEvents.value = []
  if (!aiText.value.trim() || !detail.value) return
  aiLoading.value = true
  try {
    aiEvents.value = await aiExtractTracks(detail.value.id, aiText.value)
  } catch (e) {
    aiErr.value = errMsg(e)
  } finally {
    aiLoading.value = false
  }
}
async function confirmAiEvent(ev: { category: string; title: string; content: string }) {
  if (!detail.value) return
  try {
    await createTrack(detail.value.id, { category: ev.category || '其他', title: ev.title || '', content: ev.content })
    tracks.value = await listTracks(detail.value.id)
  } catch (e) {
    alert(errMsg(e))
  }
}

// ---------- 违约事项 ----------
const breachDlg = reactive({ show: false })
const breachForm = reactive({ breach_party: '上游', breach_content: '', solution: '' })
const breachErr = ref('')
async function saveBreach() {
  breachErr.value = ''
  if (!breachForm.breach_content.trim()) {
    breachErr.value = '请填写违约事项'
    return
  }
  if (!detail.value) return
  try {
    await createBreach(detail.value.id, { ...breachForm })
    breachDlg.show = false
    Object.assign(breachForm, { breach_party: '上游', breach_content: '', solution: '' })
    breaches.value = await listBreaches(detail.value.id)
  } catch (e) {
    breachErr.value = errMsg(e)
  }
}
async function setBreachStatus(b: Breach, status: string) {
  try {
    await updateBreach(b.id, { status })
    breaches.value = await listBreaches(detail.value!.id)
  } catch (e) {
    alert(errMsg(e))
  }
}

function fmt(t: string | null) {
  return t ? t.replace('T', ' ').slice(0, 16) : '—'
}
function sname(id: number | null) {
  if (id == null) return '—'
  return suppliers.value.find((s) => s.id === id)?.name || `#${id}`
}
function cname(id: number | null) {
  if (id == null) return '—'
  return customers.value.find((c) => c.id === id)?.name || `#${id}`
}
</script>

<template>
  <div>
    <div class="bg-white rounded-xl border border-line">
      <div class="flex items-center gap-3 p-4 border-b border-line flex-wrap">
        <input v-model="keyword" :class="inputCls + ' w-52'" placeholder="搜索订单号/协议号/参与方名称" @keyup.enter="load" />
        <select v-model="statusFilter" :class="inputCls + ' w-40'" @change="load">
          <option value="">全部状态</option>
          <option v-for="(m, k) in ORDER_STATUSES" :key="k" :value="k">{{ m.label }}</option>
        </select>
        <button class="px-5 py-2.5 rounded-lg text-[13px] border border-line text-muted hover:bg-slate-50 transition" @click="load">搜索</button>
        <button class="ml-auto px-5 py-2.5 rounded-lg text-[13px] bg-primary text-white transition whitespace-nowrap shrink-0" @click="openCreate">+ 录入订单</button>
      </div>
      <table class="w-full text-sm">
        <thead>
          <tr class="text-left text-muted text-[13px] border-b border-line">
            <th class="px-5 py-3.5 font-medium">订单号</th>
            <th class="px-5 py-3.5 font-medium">产品</th>
            <th class="px-5 py-3.5 font-medium">数量/金额</th>
            <th class="px-5 py-3.5 font-medium">供货方</th>
            <th class="px-5 py-3.5 font-medium">客户</th>
            <th class="px-5 py-3.5 font-medium">采购方式</th>
            <th class="px-5 py-3.5 font-medium">状态</th>
            <th class="px-5 py-3.5 font-medium">更新</th>
            <th class="px-5 py-3.5 font-medium text-right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading"><td colspan="9" class="px-5 py-8 text-center text-muted">加载中…</td></tr>
          <tr v-else-if="!rows.length"><td colspan="9" class="px-5 py-8 text-center text-muted">暂无订单,点击右上角录入</td></tr>
          <tr v-for="o in rows" :key="o.id" class="border-b border-line hover:bg-slate-50/60 transition">
            <td class="px-5 py-3.5 font-medium">{{ o.order_no }}</td>
            <td class="px-5 py-3.5 text-muted">{{ products.find((p) => p.id === o.product_line_id)?.name || '—' }}</td>
            <td class="px-5 py-3.5" style="font-variant-numeric: tabular-nums">{{ o.quantity }} 台 / {{ o.total_amount != null ? o.total_amount.toLocaleString() : '—' }}</td>
            <td class="px-5 py-3.5 text-muted">{{ sname(o.supplier_id) }}</td>
            <td class="px-5 py-3.5 text-muted">{{ cname(o.customer_id) }}</td>
            <td class="px-5 py-3.5 text-muted">{{ o.payment_mode || '—' }}</td>
            <td class="px-5 py-3.5"><span class="text-xs px-2 py-0.5 rounded" :class="ORDER_STATUSES[o.status]?.cls">{{ ORDER_STATUSES[o.status]?.label || o.status }}</span></td>
            <td class="px-5 py-3.5 text-muted text-xs">{{ fmt(o.updated_at) }}</td>
            <td class="px-5 py-3.5 text-right whitespace-nowrap">
              <button class="text-[13px] text-primary hover:underline mr-3" @click="openDetail(o)">跟踪</button>
              <button class="text-[13px] text-primary hover:underline mr-3" @click="openEdit(o)">编辑</button>
              <button class="text-[13px] text-red-500 hover:underline" @click="remove(o)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 录入/编辑弹窗 -->
    <div v-if="dlg.show" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50" @click.self="dlg.show = false">
      <div class="bg-white rounded-xl w-[640px] max-h-[88vh] overflow-y-auto shadow-2xl">
        <div class="px-6 py-4 border-b border-line sticky top-0 bg-white rounded-t-xl">
          <div class="text-base font-bold">{{ dlg.target ? '编辑订单' : '录入订单(协议签订)' }}</div>
        </div>
        <div class="p-6 grid grid-cols-2 gap-4">
          <div><label :class="labelCls">订单编号 *</label><input v-model="form.order_no" :class="inputCls" /></div>
          <div><label :class="labelCls">产品型号</label><select v-model="form.product_line_id" :class="inputCls"><option :value="null">未选择</option><option v-for="p in products" :key="p.id" :value="p.id">{{ p.name }}</option></select></div>
          <div><label :class="labelCls">数量</label><input v-model="form.quantity" type="number" :class="inputCls" /></div>
          <div><label :class="labelCls">币种</label><select v-model="form.currency" :class="inputCls"><option value="CNY">CNY</option><option value="USD">USD</option><option value="HKD">HKD</option></select></div>
          <div><label :class="labelCls">单价</label><input v-model="form.unit_price" type="number" :class="inputCls" /></div>
          <div><label :class="labelCls">总金额</label><input v-model="form.total_amount" type="number" :class="inputCls" /></div>
          <div><label :class="labelCls">上游供货方</label><select v-model="form.supplier_id" :class="inputCls"><option :value="null">未选择</option><option v-for="s in suppliers" :key="s.id" :value="s.id">{{ s.name }}</option></select></div>
          <div><label :class="labelCls">下游客户</label><select v-model="form.customer_id" :class="inputCls"><option :value="null">未选择</option><option v-for="c in customers" :key="c.id" :value="c.id">{{ c.name }}</option></select></div>
          <div><label :class="labelCls">采购方式</label><select v-model="form.payment_mode" :class="inputCls"><option v-for="m in ['预付款', '信用证-国内', '信用证-跨境']" :key="m" :value="m">{{ m }}</option></select></div>
          <div><label :class="labelCls">协议编号</label><input v-model="form.contract_no" :class="inputCls" /></div>
          <div><label :class="labelCls">签订时间</label><input v-model="form.signed_at" type="date" :class="inputCls" /></div>
        </div>
        <div class="px-6 py-4 border-t border-line flex items-center justify-end gap-2 sticky bottom-0 bg-white rounded-b-xl">
          <p v-if="formErr" class="text-[13px] text-red-500 mr-auto">{{ formErr }}</p>
          <button class="px-5 py-2.5 rounded-lg text-[13px] border border-line text-muted" @click="dlg.show = false">取消</button>
          <button class="px-5 py-2.5 rounded-lg text-[13px] bg-primary text-white" @click="submit">保存</button>
        </div>
      </div>
    </div>

    <!-- 详情抽屉 -->
    <template v-if="detail">
      <div class="fixed inset-0 bg-black/40 z-40" @click.self="detail = null"></div>
      <div class="fixed inset-y-0 right-0 w-[760px] max-w-[94vw] bg-white shadow-2xl z-50 flex flex-col">
        <div class="px-6 py-4 border-b border-line flex items-center shrink-0">
          <div>
            <div class="text-base font-bold">{{ detail!.order_no }}
              <span class="text-xs px-2 py-0.5 rounded ml-2" :class="ORDER_STATUSES[detail!.status]?.cls">{{ ORDER_STATUSES[detail!.status]?.label }}</span>
            </div>
            <div class="text-xs text-muted mt-1">{{ products.find((p) => p.id === detail!.product_line_id)?.name || '—' }} · {{ detail!.quantity }} 台 · 总额 {{ detail!.total_amount != null ? detail!.total_amount.toLocaleString() : '—' }} {{ detail!.currency }} · {{ sname(detail!.supplier_id) }} → {{ cname(detail!.customer_id) }}</div>
          </div>
          <button class="ml-auto text-2xl text-muted hover:text-navy" @click="detail = null">×</button>
        </div>
        <div class="flex-1 overflow-y-auto p-6">
          <!-- 状态步骤条 -->
          <div class="flex items-center mb-2">
            <template v-for="(s, i) in flowSteps" :key="s">
              <div class="flex flex-col items-center">
                <div class="w-4 h-4 rounded-full border-2 shrink-0" :class="flowIdx(detail.status) >= i ? 'bg-primary border-primary' : 'bg-white border-line'"></div>
                <div class="text-[10px] mt-1 whitespace-nowrap" :class="flowIdx(detail.status) >= i ? 'text-primary font-medium' : 'text-muted'">{{ ORDER_STATUSES[s].label }}</div>
              </div>
              <div v-if="i < flowSteps.length - 1" class="flex-1 h-0.5 mx-1 mb-4" :class="flowIdx(detail.status) > i ? 'bg-primary' : 'bg-line'"></div>
            </template>
          </div>

          <div class="text-xs text-muted mb-3">节点随跟踪事件自动标记(货源/资金/到货/交付逐级推进,违约事件自动进入违约分支);也可用下方按钮手动调整</div>

          <!-- 违约状态操作 -->
          <div v-if="detail.status === 'breach' || detail.status === 'breach_processing'" class="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-4 flex items-center gap-3">
            <div class="text-[13px] text-amber-700 flex-1">
              订单处于<b>{{ ORDER_STATUSES[detail.status].label }}</b>状态。{{ detail.status === 'breach_processing' ? '请跟踪违约事项履约情况,解决后订单自动回到违约前环节。' : '补充违约事项后进入违约处理中。' }}
            </div>
            <button v-if="detail.status === 'breach'" class="px-4 py-2 rounded-lg text-[13px] bg-amber-500 text-white" @click="changeOrderStatus(detail!.id, 'breach_processing').then(() => openDetail(detail!))">进入处理中</button>
            <button v-else class="px-4 py-2 rounded-lg text-[13px] bg-primary text-white" @click="resolveBreach(detail!)">违约已解决</button>
            <button v-if="detail.status === 'breach_processing'" class="px-4 py-2 rounded-lg text-[13px] border border-line text-muted" @click="changeOrderStatus(detail!.id, 'closed').then(() => openDetail(detail!))">订单关闭</button>
          </div>
          <div v-else-if="detail.status !== 'done' && detail.status !== 'closed'" class="flex gap-2 mb-4">
            <button class="px-4 py-2 rounded-lg text-[13px] bg-primary text-white" @click="advance(detail!)">推进下一环节({{ ORDER_STATUSES[flowSteps[flowIdx(detail.status) + 1]]?.label }})</button>
            <button class="px-4 py-2 rounded-lg text-[13px] border border-red-200 text-red-500" @click="toBreach(detail!)">标记违约</button>
          </div>

          <!-- AI 摘要 -->
          <div class="bg-white border border-line rounded-xl p-4 mb-4">
            <div class="flex items-center gap-2 mb-2">
              <div class="text-[13px] font-bold text-primary">AI 订单摘要</div>
              <button class="text-xs border border-primary text-primary px-3 py-1 rounded-lg disabled:opacity-60" :disabled="aiSummaryLoading" @click="doAiSummary">{{ aiSummaryLoading ? '生成中…' : aiSummary ? '重新生成' : '生成摘要' }}</button>
            </div>
            <div v-if="aiSummary" class="text-[13px] whitespace-pre-wrap">{{ aiSummary }}</div>
            <div v-else class="text-xs text-muted">基于订单信息与跟踪事件时间线,一键生成进度概括与下一步建议</div>
          </div>

          <!-- 合同文件(全生命周期留痕) -->
          <div class="bg-white border border-line rounded-xl p-4 mb-4">
            <div class="flex items-center gap-2 mb-2">
              <div class="text-[13px] font-bold text-primary">合同文件(模版/定稿扫描件)</div>
              <span class="text-xs text-muted">全程留痕,可追溯</span>
            </div>
            <div v-for="d in docs" :key="d.id" class="flex items-center gap-2 text-xs border-b border-line last:border-0 py-2">
              <span class="px-1.5 py-0.5 rounded" :class="d.doc_type === '定稿扫描件' ? 'bg-green-50 text-green-600' : d.doc_type === '模版' ? 'bg-blue-50 text-blue-600' : 'bg-slate-100 text-slate-600'">{{ d.doc_type }}</span>
              <span class="font-medium">{{ d.file_name }}</span>
              <span v-if="d.note" class="text-muted">{{ d.note }}</span>
              <span class="text-muted">{{ d.uploaded_by_name }} · {{ fmt(d.created_at) }}</span>
              <a v-if="d.file_path" :href="`/api/files/${d.file_path}`" target="_blank" class="text-primary hover:underline ml-auto">查看</a>
              <button class="text-red-500 hover:underline" @click="removeDoc(d)">删除</button>
            </div>
            <div v-if="!docs.length" class="text-xs text-muted py-1">暂无合同文件</div>
            <div class="flex items-center gap-2 mt-2">
              <select v-model="docForm.doc_type" class="border border-line rounded-lg px-2.5 py-1.5 text-xs outline-none focus:border-primary bg-white">
                <option value="模版">模版</option>
                <option value="定稿扫描件">定稿扫描件</option>
                <option value="补充协议">补充协议</option>
                <option value="其他">其他</option>
              </select>
              <input v-model="docForm.note" class="border border-line rounded-lg px-2.5 py-1.5 text-xs outline-none focus:border-primary w-40" placeholder="备注(可留空)" />
              <input type="file" accept=".jpg,.jpeg,.png,.webp,.pdf" class="text-xs" @change="onDocPicked" />
              <button :disabled="docUploading" class="px-3 py-1.5 rounded-lg text-xs bg-primary disabled:opacity-60 text-white" @click="uploadDoc">{{ docUploading ? '上传中…' : '上传' }}</button>
            </div>
          </div>

          <!-- 跟踪事件 -->
          <div class="flex items-center justify-between mb-2">
            <div class="text-[13px] font-bold text-primary">跟踪事件(只增不改)</div>
            <div class="flex gap-2">
              <button class="px-3 py-1.5 rounded-lg text-xs border border-primary text-primary" @click="aiDlg.show = true">AI 从沟通记录提取</button>
              <button class="px-3 py-1.5 rounded-lg text-xs bg-primary text-white" @click="trackDlg.show = true">+ 记录事件</button>
            </div>
          </div>
          <div class="border-l-2 border-line pl-4 space-y-3 mb-5">
            <div v-if="!tracks.length" class="text-xs text-muted py-2">暂无跟踪事件</div>
            <div v-for="t in tracks" :key="t.id" class="bg-white border border-line rounded-lg p-3">
              <div class="flex items-center gap-2 text-xs text-muted mb-1">
                <span class="px-1.5 py-0.5 rounded" :class="TRACK_CAT_CLS[t.category] || TRACK_CAT_CLS['其他']">{{ t.category }}</span>
                <b v-if="t.title">{{ t.title }}</b>
                <span>{{ fmt(t.created_at) }}</span>
                <span>·</span>
                <span>{{ t.created_by_name }}</span>
              </div>
              <div class="text-[13px] whitespace-pre-wrap">{{ t.content }}</div>
            </div>
          </div>

          <!-- 违约事项 -->
          <div class="flex items-center justify-between mb-2">
            <div class="text-[13px] font-bold text-primary">违约事项</div>
            <button class="px-3 py-1.5 rounded-lg text-xs bg-primary text-white" @click="breachDlg.show = true">+ 记录违约</button>
          </div>
          <div class="space-y-2">
            <div v-if="!breaches.length" class="text-xs text-muted py-1">暂无违约事项</div>
            <div v-for="b in breaches" :key="b.id" class="bg-white border border-line rounded-lg p-3">
              <div class="flex items-center gap-2 text-xs mb-1">
                <span class="px-1.5 py-0.5 rounded bg-red-50 text-red-600">{{ b.breach_party || '违约方未标注' }}</span>
                <span class="px-1.5 py-0.5 rounded" :class="b.status === '处理中' ? 'bg-amber-50 text-amber-600' : b.status === '已解决' ? 'bg-green-50 text-green-600' : 'bg-slate-100 text-slate-500'">{{ b.status }}</span>
              </div>
              <div class="text-[13px]">{{ b.breach_content }}</div>
              <div v-if="b.solution" class="text-xs text-muted mt-1">处理方案:{{ b.solution }}</div>
              <div v-if="b.status === '处理中'" class="flex gap-2 mt-2">
                <button class="text-xs text-green-600 hover:underline" @click="setBreachStatus(b, '已解决')">标记已解决</button>
                <button class="text-xs text-slate-500 hover:underline" @click="setBreachStatus(b, '已关闭')">关闭</button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 记录事件弹窗 -->
      <div v-if="trackDlg.show" class="fixed inset-0 bg-black/40 flex items-center justify-center z-[60]" @click.self="trackDlg.show = false">
        <div class="bg-white rounded-xl w-[440px] p-6 shadow-2xl">
          <div class="text-base font-bold mb-4">记录跟踪事件</div>
          <div class="grid gap-3">
            <div><label :class="labelCls">分类</label><select v-model="trackForm.category" :class="inputCls"><option v-for="c in ['货源', '资金', '到货', '交付', '违约', '其他']" :key="c" :value="c">{{ c }}</option></select></div>
            <div><label :class="labelCls">标题</label><input v-model="trackForm.title" :class="inputCls" /></div>
            <div><label :class="labelCls">内容 *</label><textarea v-model="trackForm.content" :class="inputCls" rows="4"></textarea></div>
          </div>
          <p v-if="trackErr" class="text-[13px] text-red-500 mt-2">{{ trackErr }}</p>
          <div class="flex justify-end gap-2 mt-4">
            <button class="px-5 py-2.5 rounded-lg text-[13px] border border-line text-muted" @click="trackDlg.show = false">取消</button>
            <button class="px-5 py-2.5 rounded-lg text-[13px] bg-primary text-white" @click="saveTrack">保存</button>
          </div>
        </div>
      </div>

      <!-- AI 提取弹窗 -->
      <div v-if="aiDlg.show" class="fixed inset-0 bg-black/40 flex items-center justify-center z-[60]" @click.self="aiDlg.show = false">
        <div class="bg-white rounded-xl w-[520px] max-h-[86vh] overflow-y-auto p-6 shadow-2xl relative">
          <button class="absolute top-3 right-3 w-8 h-8 rounded-lg hover:bg-slate-100 text-lg text-muted" @click="aiDlg.show = false">×</button>
          <div class="text-base font-bold mb-3">AI 从沟通记录提取跟踪事件</div>
          <textarea v-model="aiText" :class="inputCls" rows="4" placeholder="粘贴微信/邮件沟通内容,如:今天和客户确认了下周一打尾款 80%,上游说货已经到香港仓,下周安排报关"></textarea>
          <button :disabled="aiLoading" class="mt-3 px-4 py-2 rounded-lg text-[13px] bg-primary disabled:opacity-60 text-white" @click="doAiExtract">{{ aiLoading ? '提取中…' : 'AI 提取' }}</button>
          <p v-if="aiErr" class="text-[13px] text-red-500 mt-2">{{ aiErr }}</p>
          <div v-for="(ev, i) in aiEvents" :key="i" class="border border-line rounded-lg p-3 mt-3">
            <div class="flex items-center gap-2 text-xs mb-1">
              <span class="px-1.5 py-0.5 rounded" :class="TRACK_CAT_CLS[ev.category] || TRACK_CAT_CLS['其他']">{{ ev.category || '其他' }}</span>
              <b>{{ ev.title }}</b>
            </div>
            <div class="text-[13px]">{{ ev.content }}</div>
            <div v-if="ev.next_action" class="text-xs text-primary mt-1">建议下一步:{{ ev.next_action }}</div>
            <button class="mt-2 text-xs text-primary hover:underline" @click="confirmAiEvent(ev)">确认保存为跟踪事件</button>
          </div>
        </div>
      </div>

      <!-- 违约弹窗 -->
      <div v-if="breachDlg.show" class="fixed inset-0 bg-black/40 flex items-center justify-center z-[60]" @click.self="breachDlg.show = false">
        <div class="bg-white rounded-xl w-[440px] p-6 shadow-2xl">
          <div class="text-base font-bold mb-4">记录违约事项</div>
          <div class="grid gap-3">
            <div><label :class="labelCls">违约方</label><select v-model="breachForm.breach_party" :class="inputCls"><option v-for="p in ['上游', '下游', '中间层', '其他']" :key="p" :value="p">{{ p }}</option></select></div>
            <div><label :class="labelCls">违约事项 *</label><textarea v-model="breachForm.breach_content" :class="inputCls" rows="3"></textarea></div>
            <div><label :class="labelCls">处理方案</label><textarea v-model="breachForm.solution" :class="inputCls" rows="2"></textarea></div>
          </div>
          <p v-if="breachErr" class="text-[13px] text-red-500 mt-2">{{ breachErr }}</p>
          <div class="flex justify-end gap-2 mt-4">
            <button class="px-5 py-2.5 rounded-lg text-[13px] border border-line text-muted" @click="breachDlg.show = false">取消</button>
            <button class="px-5 py-2.5 rounded-lg text-[13px] bg-primary text-white" @click="saveBreach">保存</button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
