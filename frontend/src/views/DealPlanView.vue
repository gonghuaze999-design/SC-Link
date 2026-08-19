<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import html2canvas from 'html2canvas'
import {
  computePlan,
  createDealPlan,
  createFlow,
  createNode,
  deleteDealPlan,
  deleteFlow,
  deleteNode,
  updateNode,
  listDealPlans,
  listFlows,
  listNodes,
  updateDealPlan,
  updateFlow,
  type DealCompute,
  type DealFlow,
  type DealNode,
  type DealPlan,
} from '../api/deal'
import { errMsg } from '../api/http'

const plans = ref<DealPlan[]>([])
const current = ref<DealPlan | null>(null)
const nodes = ref<DealNode[]>([])
const flows = ref<DealFlow[]>([])
const calc = ref<DealCompute | null>(null)

const ROLE_META: Record<string, { label: string; cls: string; bar: string; light: string }> = {
  customer: { label: '下游客户', cls: 'text-green-600 bg-green-50', bar: '#10B981', light: '#ECFDF5' },
  middle: { label: '中间层', cls: 'text-amber-600 bg-amber-50', bar: '#F59E0B', light: '#FFFBEB' },
  supplier: { label: '上游供货方', cls: 'text-blue-600 bg-blue-50', bar: '#2563EB', light: '#EFF6FF' },
}
const FLOW_META: Record<string, string> = {
  payment: '资金支付', guarantee: '保函', lc_issue: '信用证开立', margin: '保证金',
  upfront_fee: '居间前置', supplier_return: '上游居间尾款返回', lc_fee: '开证费', goods: '货物交付', other: '其他',
}
const BASE_META: Record<string, string> = {
  downstream_total: '下游总额', upstream_total: '上游总额', spread: '总价差',
  wrapped_spread: '上游包裹价差', middle_wrapped: '中间层包裹收益',
}

async function loadPlans() {
  plans.value = await listDealPlans().catch(() => [])
  if (!current.value && plans.value.length) await openPlan(plans.value[0])
}

async function openPlan(p: DealPlan) {
  current.value = p
  await refresh()
}

async function refresh() {
  if (!current.value) return
  nodes.value = await listNodes(current.value.id).catch(() => [])
  flows.value = await listFlows(current.value.id).catch(() => [])
  calc.value = await computePlan(current.value.id).catch(() => null)
}

// ---------- 方案 ----------
const dlg = reactive({ show: false, edit: null as DealPlan | null })
const form = reactive({ title: '', quantity: 0, upstream_price: null as number | null, downstream_price: null as number | null, wrapped_spread: null as number | null, supplier_fee_fixed: null as number | null, upfront_percent: null as number | null, currency: 'CNY', payment_mode: '预付款', lc_deposit_percent: null as number | null, lc_fee_percent: null as number | null })
const formErr = ref('')
function openCreate() {
  dlg.edit = null
  Object.assign(form, { title: '', quantity: 0, upstream_price: null, downstream_price: null, wrapped_spread: null, supplier_fee_fixed: null, upfront_percent: null, currency: 'CNY', payment_mode: '预付款', lc_deposit_percent: null, lc_fee_percent: null })
  formErr.value = ''
  dlg.show = true
}
function openEditPlan(p: DealPlan) {
  dlg.edit = p
  Object.assign(form, {
    title: p.title, quantity: p.quantity, upstream_price: p.upstream_price, downstream_price: p.downstream_price,
    wrapped_spread: p.wrapped_spread, supplier_fee_fixed: p.supplier_fee_fixed, upfront_percent: p.upfront_percent,
    currency: p.currency, payment_mode: p.payment_mode, lc_deposit_percent: p.lc_deposit_percent, lc_fee_percent: p.lc_fee_percent,
  })
  formErr.value = ''
  dlg.show = true
}
async function submitPlan() {
  formErr.value = ''
  if (!form.title.trim()) {
    formErr.value = '请填写方案名称'
    return
  }
  try {
    if (dlg.edit) {
      const p = await updateDealPlan(dlg.edit.id, { ...form, version: dlg.edit.version })
      dlg.show = false
      loadPlans()
      openPlan(p)
    } else {
      const p = await createDealPlan({ ...form })
      dlg.show = false
      loadPlans()
      openPlan(p)
    }
  } catch (e) {
    formErr.value = errMsg(e)
  }
}
async function removePlan(p: DealPlan) {
  if (!window.confirm(`确认删除方案「${p.title}」?`)) return
  try {
    await deleteDealPlan(p.id)
    current.value = null
    loadPlans()
  } catch (e) {
    alert(errMsg(e))
  }
}

// ---------- 节点 ----------
const nodeDlg = reactive({ show: false, target: null as DealNode | null })
const nodeForm = reactive({ role: 'middle', name: '', seq: 0, purpose: '交易居间', fee_fixed: null as number | null, fee_percent: null as number | null, fee_base: 'downstream_total', income_fixed: null as number | null, income_percent: null as number | null, income_base: 'downstream_total', deposit_fixed: null as number | null })
const isAgency = computed(() => nodeForm.role === 'middle' && ['代开信用证', '开保函'].includes(nodeForm.purpose))
const resetNodeForm = () => Object.assign(nodeForm, { role: 'middle', name: '', seq: 0, purpose: '交易居间', fee_fixed: null, fee_percent: null, fee_base: 'downstream_total', income_fixed: null, income_percent: null, income_base: 'downstream_total', deposit_fixed: null })
function openNode(n: DealNode | null) {
  nodeDlg.target = n
  if (n) {
    Object.assign(nodeForm, {
      role: n.role, name: n.name, seq: n.seq, purpose: n.purpose || '交易居间',
      fee_fixed: n.fee_fixed, fee_percent: n.fee_percent, fee_base: n.fee_base || 'downstream_total',
      income_fixed: n.income_fixed, income_percent: n.income_percent, income_base: n.income_base || 'downstream_total',
      deposit_fixed: n.deposit_fixed,
    })
  } else {
    resetNodeForm()
  }
  nodeDlg.show = true
}
async function saveNode() {
  if (!current.value || !nodeForm.name.trim()) return
  try {
    if (nodeDlg.target) await updateNode(nodeDlg.target.id, { ...nodeForm })
    else await createNode(current.value.id, { ...nodeForm, seq: nodes.value.length + 1 })
    nodeDlg.show = false
    resetNodeForm()
    refresh()
  } catch (e) {
    alert(errMsg(e))
  }
}
async function removeNode(n: DealNode) {
  if (!window.confirm(`删除节点「${n.name}」?关联动作将一并删除。`)) return
  try {
    await deleteNode(n.id)
    refresh()
  } catch (e) {
    alert(errMsg(e))
  }
}

// ---------- 动作流 ----------
const flowDlg = reactive({ show: false, target: null as DealFlow | null })
const flowForm = reactive({ seq: 1, flow_type: 'payment', label: '', from_node_id: null as number | null, to_node_id: null as number | null, amount_type: 'percent', amount: null as number | null, percent: null as number | null, base: 'downstream_total' })
async function openFlow(f: DealFlow | null) {
  flowDlg.target = f
  if (f) {
    Object.assign(flowForm, {
      seq: f.seq, flow_type: f.flow_type, label: f.label, from_node_id: f.from_node_id,
      to_node_id: f.to_node_id, amount_type: f.amount_type, amount: f.amount,
      percent: f.percent, base: f.base,
    })
  } else {
    Object.assign(flowForm, {
      seq: flows.value.length + 1, flow_type: 'payment', label: '', from_node_id: null,
      to_node_id: null, amount_type: 'percent', amount: null, percent: null, base: 'downstream_total',
    })
  }
  flowDlg.show = true
}
async function saveFlow() {
  if (!current.value || !flowForm.label.trim()) return
  try {
    if (flowDlg.target) await updateFlow(flowDlg.target.id, { ...flowForm })
    else await createFlow(current.value.id, { ...flowForm })
    flowDlg.show = false
    refresh()
  } catch (e) {
    alert(errMsg(e))
  }
}
async function removeFlow(f: DealFlow) {
  if (!window.confirm(`删除动作「${f.label}」?`)) return
  try {
    await deleteFlow(f.id)
    refresh()
  } catch (e) {
    alert(errMsg(e))
  }
}
async function moveFlow(f: DealFlow, dir: -1 | 1) {
  const idx = flows.value.findIndex((x) => x.id === f.id)
  const other = flows.value[idx + dir]
  if (!other) return
  try {
    await updateFlow(f.id, { ...f, seq: other.seq })
    await updateFlow(other.id, { ...other, seq: f.seq })
    refresh()
  } catch (e) {
    alert(errMsg(e))
  }
}
function nodeName(id: number | null) {
  return nodes.value.find((n) => n.id === id)?.name || '—'
}
function flowAmountText(f: DealFlow) {
  if (f.amount_type === 'percent') return `${f.percent ?? '?'}% × ${BASE_META[f.base] || f.base}`
  return `${(f.amount ?? 0).toLocaleString()}`
}

// ---------- 导出 ----------
const exportDlg = reactive({ show: false })
const exportOpts = reactive({
  include_amounts: true, include_middle_income: true, include_held: true,
  include_upfront: true, include_prices: true, include_guarantee: true, include_lc: true,
})
const exportRef = ref<HTMLDivElement | null>(null)
const exporting = ref(false)
const money = (v: number) => `${(v ?? 0).toLocaleString()} 万`

async function exportPng() {
  if (!exportRef.value) return
  exporting.value = true
  try {
    const canvas = await html2canvas(exportRef.value, { scale: 2, backgroundColor: '#ffffff' })
    const a = document.createElement('a')
    a.href = canvas.toDataURL('image/png')
    a.download = `${current.value?.title || '交易链路'}-链路图.png`
    a.click()
  } catch (e) {
    alert('导出失败:' + errMsg(e))
  } finally {
    exporting.value = false
  }
}
function exportPdf() {
  window.print()
}

const totalDown = computed(() => ((current.value?.downstream_price ?? 0) * (current.value?.quantity ?? 0)))
const totalUp = computed(() => ((current.value?.upstream_price ?? 0) * (current.value?.quantity ?? 0)))

const inputCls = 'w-full border border-line rounded-lg px-3.5 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20'
const labelCls = 'block text-[13px] text-muted mb-1.5'
onMounted(loadPlans)
</script>

<template>
  <div class="flex gap-5 items-start">
    <!-- 方案列表 -->
    <div class="w-64 bg-white rounded-xl border border-line shrink-0">
      <div class="px-4 py-3 border-b border-line flex items-center">
        <div class="text-sm font-bold">交易方案</div>
        <button class="ml-auto text-[13px] bg-primary text-white px-3 py-1.5 rounded-lg" @click="openCreate()">+ 新建</button>
      </div>
      <div class="p-2 space-y-1 max-h-[70vh] overflow-y-auto">
        <div v-for="p in plans" :key="p.id" class="px-3 py-2.5 rounded-lg cursor-pointer transition text-[13px]" :class="current?.id === p.id ? 'bg-blue-50 text-primary font-medium' : 'hover:bg-slate-50'" @click="openPlan(p)">
          <div class="truncate">{{ p.title }}</div>
          <div class="text-xs text-muted mt-0.5">{{ p.quantity }} 台 · {{ p.payment_mode }}</div>
        </div>
        <div v-if="!plans.length" class="text-[13px] text-muted text-center py-6">暂无方案,点击新建</div>
      </div>
    </div>

    <!-- 编辑器 -->
    <div v-if="current" class="flex-1 min-w-0 space-y-5">
      <!-- 方案头 -->
      <div class="bg-white rounded-xl border border-line p-5 flex items-center gap-4 flex-wrap">
        <div>
          <div class="text-base font-bold">{{ current.title }}</div>
          <div class="text-xs text-muted mt-1">
            {{ current.quantity }} 台 · 上游 {{ current.upstream_price != null ? `${current.upstream_price.toLocaleString()} 万/台` : '—' }} / 下游 {{ current.downstream_price != null ? `${current.downstream_price.toLocaleString()} 万/台` : '—' }} · {{ current.payment_mode }}
            <span v-if="current.wrapped_spread != null" class="ml-3 px-2 py-0.5 rounded bg-amber-50 text-amber-700">包裹价差 {{ current.wrapped_spread.toLocaleString() }} 万/台 × {{ current.quantity }} 台 = {{ (current.wrapped_spread * current.quantity).toLocaleString() }} 万<span v-if="current.supplier_fee_fixed != null"> · 上游居间 {{ current.supplier_fee_fixed.toLocaleString() }} 万</span><span v-if="current.upfront_percent != null"> · 前置 {{ current.upfront_percent }}%</span></span>
          </div>
        </div>
        <div class="ml-auto flex gap-2">
          <button class="px-4 py-2 rounded-lg text-[13px] border border-line text-muted" @click="openEditPlan(current)">编辑</button>
          <button class="px-4 py-2 rounded-lg text-[13px] border border-primary text-primary" @click="exportDlg.show = true">导出图片/PDF</button>
          <button class="px-4 py-2 rounded-lg text-[13px] border border-red-200 text-red-500" @click="removePlan(current)">删除方案</button>
        </div>
      </div>

      <!-- 节点 -->
      <div class="bg-white rounded-xl border border-line p-5">
        <div class="flex items-center mb-3">
          <div class="text-sm font-bold">链路参与方(角色配色:绿=客户 / 琥珀=中间层 / 蓝=供货方)</div>
          <button class="ml-auto px-3 py-1.5 rounded-lg text-xs bg-primary text-white" @click="openNode(null)">+ 添加参与方</button>
        </div>
        <div class="grid grid-cols-3 gap-4">
          <div v-for="n in nodes" :key="n.id" class="rounded-xl border-2 p-4" :style="{ borderColor: ROLE_META[n.role]?.bar, background: ROLE_META[n.role]?.light }">
            <div class="flex items-center gap-2">
              <span class="text-xs px-2 py-0.5 rounded font-medium" :class="ROLE_META[n.role]?.cls">{{ ROLE_META[n.role]?.label }}</span>
              <span v-if="n.role === 'middle'" class="text-xs px-1.5 py-0.5 rounded bg-white/70" :class="['代开信用证', '开保函'].includes(n.purpose) ? 'text-purple-600' : 'text-amber-600'">{{ n.purpose }}</span>
              <button class="ml-auto text-xs text-primary hover:underline mr-2" @click="openNode(n)">编辑</button>
              <button class="text-xs text-red-500 hover:underline" @click="removeNode(n)">删除</button>
            </div>
            <div class="text-[15px] font-bold mt-2">{{ n.name }}</div>
            <div v-if="calc" class="text-xs mt-2 space-y-0.5" style="font-variant-numeric: tabular-nums">
              <div>收 {{ money(calc.nodes.find((x) => x.node_id === n.id)?.receive_total ?? 0) }}</div>
              <div>付 {{ money(calc.nodes.find((x) => x.node_id === n.id)?.paid_total ?? 0) }}</div>
              <div class="font-medium">净 {{ money(calc.nodes.find((x) => x.node_id === n.id)?.net ?? 0) }}</div>
            </div>
          </div>
          <div v-if="!nodes.length" class="col-span-3 text-[13px] text-muted text-center py-4">先添加参与方(客户/中间层/供货方),再编排动作流</div>
        </div>
      </div>

      <!-- 动作流 -->
      <div class="bg-white rounded-xl border border-line p-5">
        <div class="flex items-center mb-3">
          <div class="text-sm font-bold">资金与保障动作(按次序执行,可增删排序)</div>
          <button class="ml-auto px-3 py-1.5 rounded-lg text-xs bg-primary text-white" @click="openFlow(null)">+ 添加动作</button>
        </div>
        <div class="space-y-2">
          <div v-for="(f, i) in [...flows].sort((a, b) => a.seq - b.seq)" :key="f.id" class="flex items-center gap-3 border border-line rounded-lg px-4 py-2.5">
            <span class="w-6 h-6 rounded-full bg-navy text-white text-xs flex items-center justify-center shrink-0">{{ f.seq }}</span>
            <span class="text-xs px-2 py-0.5 rounded bg-slate-100 shrink-0">{{ FLOW_META[f.flow_type] || f.flow_type }}</span>
            <span class="text-[13px] font-medium">{{ f.label }}</span>
            <span class="text-xs text-muted">{{ nodeName(f.from_node_id) }} → {{ nodeName(f.to_node_id) }}</span>
            <span class="text-xs text-muted shrink-0" style="font-variant-numeric: tabular-nums">{{ flowAmountText(f) }}</span>
            <div class="ml-auto flex items-center gap-2 shrink-0">
              <button class="text-xs text-muted hover:text-navy disabled:opacity-30" :disabled="i === 0" @click="moveFlow(f, -1)">↑</button>
              <button class="text-xs text-muted hover:text-navy disabled:opacity-30" :disabled="i === flows.length - 1" @click="moveFlow(f, 1)">↓</button>
              <button class="text-xs text-primary hover:underline" @click="openFlow(f)">编辑</button>
              <button class="text-xs text-red-500 hover:underline" @click="removeFlow(f)">删除</button>
            </div>
          </div>
          <div v-if="!flows.length" class="text-[13px] text-muted text-center py-4">暂无动作:如「客户预付 20% → 中间层」「中间层向客户开保函 30%」「上游居间前置(价差 15%)→ 中间层」</div>
        </div>
      </div>

      <!-- 测算 -->
      <div v-if="calc" class="bg-white rounded-xl border border-line p-5">
        <div class="text-sm font-bold mb-3">测算结果</div>
        <div class="grid grid-cols-4 gap-4 mb-4">
          <div class="rounded-xl border border-line p-4"><div class="text-xs text-muted">下游总额</div><div class="text-xl font-bold mt-1" style="font-variant-numeric: tabular-nums">{{ money(totalDown) }}</div></div>
          <div class="rounded-xl border border-line p-4"><div class="text-xs text-muted">上游总额</div><div class="text-xl font-bold mt-1" style="font-variant-numeric: tabular-nums">{{ money(totalUp) }}</div></div>
          <div class="rounded-xl border border-line p-4" style="background:#FFFBEB"><div class="text-xs text-muted">总价差(中间层收益点①)</div><div class="text-xl font-bold mt-1 text-amber-600" style="font-variant-numeric: tabular-nums">{{ money(calc.spread) }}</div></div>
          <div v-if="calc.lc_cost" class="rounded-xl border border-line p-4"><div class="text-xs text-muted">代开证成本(保证金+费率)</div><div class="text-xl font-bold mt-1" style="font-variant-numeric: tabular-nums">{{ money(calc.lc_cost.total) }}</div><div class="text-xs text-muted mt-1">保证金 {{ money(calc.lc_cost.deposit) }} + 开证费 {{ money(calc.lc_cost.fee) }}</div></div>
        </div>
        <div v-for="m in calc.middle_metrics" :key="m.node_id" class="rounded-xl border-2 p-4 mb-3" style="border-color:#F59E0B; background:#FFFBEB">
          <div v-if="['代开信用证', '开保函'].includes(m.purpose)" class="text-sm font-bold text-amber-600 mb-2">{{ m.name }} · {{ m.purpose }}收益(代开费用+收益)</div>
          <div v-else class="text-sm font-bold text-amber-600 mb-2">{{ m.name }} · 中间层收益三要点</div>
          <div v-if="['代开信用证', '开保函'].includes(m.purpose)" class="grid grid-cols-3 gap-3 text-[13px]" style="font-variant-numeric: tabular-nums">
            <div>代开费用(交银行):<b class="text-amber-600">{{ money(m.fee_amount) }}</b></div>
            <div>收益(定额/比例):<b class="text-amber-600">{{ money(m.income_amount) }}</b></div>
            <div>保证金(押金,不计收益):<b>{{ money(m.deposit) }}</b></div>
          </div>
          <div v-else class="grid grid-cols-3 gap-3 text-[13px]" style="font-variant-numeric: tabular-nums">
            <div>① 上下游价差:<b class="text-amber-600">{{ money(calc.spread) }}</b></div>
            <div>② 截流资金峰值(代管资金):<b class="text-amber-600">{{ money(m.held_peak) }}</b><div class="text-xs text-muted">时点余额(动作结清后) {{ money(m.held_final) }}</div></div>
            <div>③ 居间前置(上游提前返):<b class="text-amber-600">{{ money(m.upfront_amount || m.upfront_fee) }}</b><div class="text-xs text-muted">动作流实际入账(动作列表里编排的金额) {{ money(m.upfront_fee) }}</div></div>
          </div>
          <div v-if="m.wrapped_spread_total > 0 && !['代开信用证', '开保函'].includes(m.purpose)" class="mt-3 border-t border-amber-200 pt-3 text-xs" style="font-variant-numeric: tabular-nums">
            <div class="font-bold text-amber-700 mb-1.5">包裹价差构成({{ current.wrapped_spread != null ? `${current.wrapped_spread.toLocaleString()} 万/台 × ${current.quantity} 台` : '未填写' }})</div>
            <div class="grid grid-cols-4 gap-2">
              <div>包裹价差总额:<b>{{ money(m.wrapped_spread_total) }}</b></div>
              <div>− 上游居间定额(完成后给):<b>{{ money(m.supplier_fee_fixed) }}</b></div>
              <div>= 中间层包裹收益:<b class="text-amber-600">{{ money(m.middle_wrapped) }}</b></div>
              <div>其中前置 {{ current.upfront_percent ?? '—' }}%:<b class="text-amber-600">{{ money(m.upfront_amount) }}</b><div class="text-muted">剩余 {{ money(m.upfront_remain) }} 完成后分配</div></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 方案弹窗 -->
    <div v-if="dlg.show" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50" @click.self="dlg.show = false">
      <div class="bg-white rounded-xl w-[520px] p-6 shadow-2xl">
        <div class="text-base font-bold mb-4">{{ dlg.edit ? "编辑交易方案" : "新建交易方案" }}</div>
        <div class="grid grid-cols-2 gap-3">
          <div class="col-span-2"><label :class="labelCls">方案名称 *</label><input v-model="form.title" :class="inputCls" placeholder="如:B300 三方链路 · 预付款+保函" /></div>
          <div><label :class="labelCls">数量</label><input v-model="form.quantity" type="number" :class="inputCls" /></div>
          <div><label :class="labelCls">采购方式</label><select v-model="form.payment_mode" :class="inputCls"><option value="预付款">预付款</option><option value="信用证-国内">信用证-国内</option><option value="信用证-跨境">信用证-跨境</option></select></div>
          <div><label :class="labelCls">上游真实供货价(万元/台)</label><input v-model="form.upstream_price" type="number" :class="inputCls" placeholder="如 136" /></div>
          <div><label :class="labelCls">下游单价(万元/台)</label><input v-model="form.downstream_price" type="number" :class="inputCls" placeholder="如 142" /></div>
          <div class="col-span-2 text-xs font-bold text-primary pt-1">包裹价差(万元,直接输入;拆分给上游居间与中间层)</div>
          <div><label :class="labelCls">上游包裹价差(万元/台,单台)</label><input v-model="form.wrapped_spread" type="number" :class="inputCls" placeholder="如 3" /></div>
          <div><label :class="labelCls">上游居间定额(万元,交易完成后给)</label><input v-model="form.supplier_fee_fixed" type="number" :class="inputCls" placeholder="如 30" /></div>
          <div><label :class="labelCls">居间前置比例 %(通常 10-30)</label><input v-model="form.upfront_percent" type="number" :class="inputCls" placeholder="基于中间层包裹收益" /></div>
          <template v-if="form.payment_mode.startsWith('信用证')">
            <div><label :class="labelCls">开证保证金比例 %</label><input v-model="form.lc_deposit_percent" type="number" :class="inputCls" placeholder="如 20" /></div>
            <div><label :class="labelCls">代开证费率 %(通常 1-3)</label><input v-model="form.lc_fee_percent" type="number" :class="inputCls" placeholder="如 1.5" /></div>
          </template>
        </div>
        <p v-if="formErr" class="text-[13px] text-red-500 mt-3">{{ formErr }}</p>
        <div class="flex justify-end gap-2 mt-5">
          <button class="px-5 py-2.5 rounded-lg text-[13px] border border-line text-muted" @click="dlg.show = false">取消</button>
          <button class="px-5 py-2.5 rounded-lg text-[13px] bg-primary text-white" @click="submitPlan">创建</button>
        </div>
      </div>
    </div>

    <!-- 节点弹窗 -->
    <div v-if="nodeDlg.show" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50" @click.self="nodeDlg.show = false">
      <div class="bg-white rounded-xl w-[400px] p-6 shadow-2xl">
        <div class="text-base font-bold mb-4">{{ nodeDlg.target ? "编辑参与方" : "添加参与方" }}</div>
        <div class="grid gap-3">
          <div><label :class="labelCls">角色</label><select v-model="nodeForm.role" :class="inputCls"><option value="customer">下游客户(绿)</option><option value="middle">中间层(琥珀)</option><option value="supplier">上游供货方(蓝)</option></select></div>
          <div><label :class="labelCls">名称 *</label><input v-model="nodeForm.name" :class="inputCls" /></div>
          <div v-if="nodeForm.role === 'middle'">
            <label :class="labelCls">功能定位</label>
            <select v-model="nodeForm.purpose" :class="inputCls">
              <option value="交易居间">交易居间(价差/截流/前置)</option>
              <option value="代开信用证">代开信用证(代开费用+收益)</option>
              <option value="开保函">开保函(代开费用+收益)</option>
              <option value="其他">其他</option>
            </select>
          </div>
          <template v-if="isAgency">
            <div class="col-span-1 text-xs font-bold text-primary">收益模型(万元):代开费用交银行,收益为定额或比例;保证金为押金不计收益</div>
            <div><label :class="labelCls">代开费用定额(万元)</label><input v-model="nodeForm.fee_fixed" type="number" :class="inputCls" placeholder="定额" /></div>
            <div><label :class="labelCls">代开费用比例 %(如 1.5)</label><input v-model="nodeForm.fee_percent" type="number" :class="inputCls" placeholder="比例,基数下方选择" /></div>
            <div><label :class="labelCls">费用基数</label><select v-model="nodeForm.fee_base" :class="inputCls"><option v-for="(l, k) in BASE_META" :key="k" :value="k">{{ l }}</option></select></div>
            <div><label :class="labelCls">收益定额(万元)</label><input v-model="nodeForm.income_fixed" type="number" :class="inputCls" placeholder="定额" /></div>
            <div><label :class="labelCls">收益比例 %</label><input v-model="nodeForm.income_percent" type="number" :class="inputCls" placeholder="比例" /></div>
            <div><label :class="labelCls">收益基数</label><select v-model="nodeForm.income_base" :class="inputCls"><option v-for="(l, k) in BASE_META" :key="k" :value="k">{{ l }}</option></select></div>
            <div><label :class="labelCls">保证金/押金(万元,不计收益)</label><input v-model="nodeForm.deposit_fixed" type="number" :class="inputCls" placeholder="押金" /></div>
          </template>
        </div>
        <div class="flex justify-end gap-2 mt-5">
          <button class="px-5 py-2.5 rounded-lg text-[13px] border border-line text-muted" @click="nodeDlg.show = false">取消</button>
          <button class="px-5 py-2.5 rounded-lg text-[13px] bg-primary text-white" @click="saveNode">添加</button>
        </div>
      </div>
    </div>

    <!-- 动作弹窗 -->
    <div v-if="flowDlg.show" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50" @click.self="flowDlg.show = false">
      <div class="bg-white rounded-xl w-[480px] p-6 shadow-2xl">
        <div class="text-base font-bold mb-4">{{ flowDlg.target ? '编辑动作' : '添加动作' }}</div>
        <div class="grid grid-cols-2 gap-3">
          <div><label :class="labelCls">类型</label><select v-model="flowForm.flow_type" :class="inputCls"><option v-for="(l, k) in FLOW_META" :key="k" :value="k">{{ l }}</option></select></div>
          <div><label :class="labelCls">次序</label><input v-model="flowForm.seq" type="number" :class="inputCls" /></div>
          <div class="col-span-2"><label :class="labelCls">说明 *</label><input v-model="flowForm.label" :class="inputCls" placeholder="如:客户预付 20%" /></div>
          <div><label :class="labelCls">从(付款方)</label><select v-model="flowForm.from_node_id" :class="inputCls"><option :value="null">—</option><option v-for="n in nodes" :key="n.id" :value="n.id">{{ n.name }}</option></select></div>
          <div><label :class="labelCls">到(收款方)</label><select v-model="flowForm.to_node_id" :class="inputCls"><option :value="null">—</option><option v-for="n in nodes" :key="n.id" :value="n.id">{{ n.name }}</option></select></div>
          <div><label :class="labelCls">金额方式</label><select v-model="flowForm.amount_type" :class="inputCls"><option value="fixed">固定金额</option><option value="percent">比例</option></select></div>
          <div><label :class="labelCls">基数(比例时)</label><select v-model="flowForm.base" :class="inputCls"><option v-for="(l, k) in BASE_META" :key="k" :value="k">{{ l }}</option></select></div>
          <div v-if="flowForm.amount_type === 'fixed'"><label :class="labelCls">金额(万元)</label><input v-model="flowForm.amount" type="number" :class="inputCls" /></div>
          <div v-else><label :class="labelCls">比例 %</label><input v-model="flowForm.percent" type="number" :class="inputCls" placeholder="如 20" /></div>
          <div v-if="['wrapped_spread', 'middle_wrapped'].includes(flowForm.base)" class="col-span-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
            基数说明:上游包裹价差 = <b>{{ current?.wrapped_spread != null ? current.wrapped_spread + ' 万/台 × ' + (current.quantity ?? 0) + ' 台 = ' + (current.wrapped_spread * (current.quantity ?? 0)).toLocaleString() + ' 万' : '未填写(在方案区右上角「编辑」中填写)' }}</b>
            <span v-if="current?.supplier_fee_fixed != null">;中间层包裹收益 = 包裹价差总额 − 上游居间定额 {{ current.supplier_fee_fixed }} 万 = <b>{{ ((current.wrapped_spread ?? 0) * (current.quantity ?? 0) - current.supplier_fee_fixed).toLocaleString() }} 万</b></span>
          </div>
        </div>
        <div class="flex justify-end gap-2 mt-5">
          <button class="px-5 py-2.5 rounded-lg text-[13px] border border-line text-muted" @click="flowDlg.show = false">取消</button>
          <button class="px-5 py-2.5 rounded-lg text-[13px] bg-primary text-white" @click="saveFlow">保存</button>
        </div>
      </div>
    </div>

    <!-- 导出弹窗 -->
    <div v-if="exportDlg.show" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50" @click.self="exportDlg.show = false">
      <div class="bg-white rounded-xl w-[560px] max-h-[88vh] overflow-y-auto p-6 shadow-2xl">
        <div class="text-base font-bold mb-2">导出交易链路(可交给上下游确认)</div>
        <div class="text-xs text-muted mb-4">勾选需要输出的内容;不勾选的项在导出文件中隐藏,适合隐藏中间层收益等敏感信息</div>
        <div class="grid grid-cols-2 gap-2 mb-4">
          <label class="flex items-center gap-2 text-[13px]"><input type="checkbox" v-model="exportOpts.include_amounts" /> 包含金额</label>
          <label class="flex items-center gap-2 text-[13px]"><input type="checkbox" v-model="exportOpts.include_prices" /> 包含上下游单价</label>
          <label class="flex items-center gap-2 text-[13px]"><input type="checkbox" v-model="exportOpts.include_middle_income" /> 包含中间层收益(价差)</label>
          <label class="flex items-center gap-2 text-[13px]"><input type="checkbox" v-model="exportOpts.include_held" /> 包含截流资金</label>
          <label class="flex items-center gap-2 text-[13px]"><input type="checkbox" v-model="exportOpts.include_upfront" /> 包含居间前置</label>
          <label class="flex items-center gap-2 text-[13px]"><input type="checkbox" v-model="exportOpts.include_guarantee" /> 包含保函细节</label>
          <label class="flex items-center gap-2 text-[13px]"><input type="checkbox" v-model="exportOpts.include_lc" /> 包含信用证/保证金</label>
        </div>
        <div class="flex gap-2 mb-4">
          <button :disabled="exporting" class="px-5 py-2.5 rounded-lg text-[13px] bg-primary disabled:opacity-60 text-white" @click="exportPng">{{ exporting ? '生成中…' : '导出 PNG 图片' }}</button>
          <button class="px-5 py-2.5 rounded-lg text-[13px] border border-primary text-primary" @click="exportPdf">导出 PDF(打印)</button>
        </div>
        <!-- 导出视图(截图目标;打印时仅显示此区域) -->
        <div ref="exportRef" class="export-area border border-line rounded-xl p-5 bg-white">
          <div class="text-center mb-3">
            <div class="text-base font-bold">{{ current?.title }}</div>
            <div class="text-xs text-muted">{{ current?.quantity }} 台 · {{ current?.payment_mode }}<span v-if="exportOpts.include_prices"> · 上游 {{ current?.upstream_price?.toLocaleString() }} / 下游 {{ current?.downstream_price?.toLocaleString() }} {{ current?.currency }}</span></div>
          </div>
          <div v-for="f in [...flows].sort((a, b) => a.seq - b.seq)" :key="f.id" class="flex items-center gap-2 text-xs py-1.5 border-b border-dashed border-line">
            <span class="text-slate-400">{{ f.seq }}.</span>
            <span>{{ FLOW_META[f.flow_type] }}</span>
            <b>{{ f.label }}</b>
            <span class="text-muted">{{ nodeName(f.from_node_id) }} → {{ nodeName(f.to_node_id) }}</span>
            <span v-if="exportOpts.include_amounts" style="font-variant-numeric: tabular-nums">{{ flowAmountText(f) }}</span>
            <span v-else class="text-muted">(金额已隐藏)</span>
          </div>
          <div v-if="calc && exportOpts.include_middle_income" class="mt-3 text-xs border rounded-lg p-3" style="background:#FFFBEB">
            <div class="font-bold text-amber-600 mb-1">中间层收益</div>
            <div v-if="exportOpts.include_amounts">价差 {{ money(calc.spread) }}<span v-if="exportOpts.include_upfront"> · 居间前置 {{ money(calc.middle_metrics[0]?.upfront_fee ?? 0) }}</span><span v-if="exportOpts.include_held"> · 截流峰值 {{ money(calc.middle_metrics[0]?.held_peak ?? 0) }}</span></div>
            <div v-else class="text-muted">(金额已隐藏)</div>
          </div>
          <div class="text-[10px] text-slate-400 text-center mt-3">SC-Link 供应链协同中台 · 本文件仅用于交易链路确认</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style>
@media print {
  body * { visibility: hidden; }
  .export-area, .export-area * { visibility: visible; }
  .export-area { position: fixed; left: 0; top: 0; width: 100%; border: none; }
}
</style>
