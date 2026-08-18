<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { listCustomers, listUserOptions, type Customer } from '../api/entities'
import {
  createDetailRequest,
  listDetailRequests,
  listPriorities,
  listPublications,
  respondDetailRequest,
  runMatch,
  setPriority,
  type DetailRequest,
  type MatchResultItem,
  type Publication,
} from '../api/match'
import { errMsg } from '../api/http'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const customers = ref<Customer[]>([])
const demandPubs = ref<Publication[]>([])
const userNames = ref<Record<number, string>>({})

const sourceType = ref<'customer' | 'publication'>('customer')
const customerId = ref<number | null>(null)
const publicationId = ref<number | null>(null)
const matching = ref(false)
const results = ref<MatchResultItem[]>([])
const filtered = ref<{ supplier_id: number; name: string; reason: string }[]>([])
const priorities = ref<Record<number, number>>({})
const pendingReqs = ref<DetailRequest[]>([])
const reqNote = ref('')
const matchErr = ref('')

async function loadBase() {
  customers.value = await listCustomers().catch(() => [])
  demandPubs.value = (await listPublications({ type: 'demand', status: 'active' }).catch(() => [])).filter((p) => p.user_id === auth.user?.id)
  userNames.value = Object.fromEntries((await listUserOptions().catch(() => [])).map((u) => [u.id, u.display_name || u.username]))
  const prs = await listPriorities().catch(() => [])
  priorities.value = Object.fromEntries(prs.filter((p) => p.entity_type === 'supplier').map((p) => [p.entity_id, p.priority]))
  pendingReqs.value = (await listDetailRequests('pending').catch(() => [])).filter((r) => r.status === 'pending')
  if (customers.value.length) customerId.value = customers.value[0].id
  if (demandPubs.value.length) publicationId.value = demandPubs.value[0].id
}
onMounted(loadBase)

async function doMatch() {
  matchErr.value = ''
  results.value = []
  filtered.value = []
  if (sourceType.value === 'customer' && !customerId.value) {
    matchErr.value = '请选择需求来源(客户)'
    return
  }
  if (sourceType.value === 'publication' && !publicationId.value) {
    matchErr.value = '请选择需求来源(发布)'
    return
  }
  matching.value = true
  try {
    const r = await runMatch(
      sourceType.value === 'customer' ? { customer_id: customerId.value! } : { publication_id: publicationId.value! },
    )
    results.value = r.results
    filtered.value = r.filtered
  } catch (e) {
    matchErr.value = errMsg(e)
  } finally {
    matching.value = false
  }
}

async function requestFull(r: MatchResultItem) {
  const note = window.prompt('申请查看全量信息,备注(可留空):') || ''
  try {
    await createDetailRequest('supplier', r.entity.id, note)
    alert('申请已提交,等待数据维护人审批')
  } catch (e) {
    alert(errMsg(e))
  }
}

async function respond(req: DetailRequest, action: 'approve' | 'reject') {
  try {
    await respondDetailRequest(req.id, action)
    loadBase()
  } catch (e) {
    alert(errMsg(e))
  }
}

async function quickPriority(r: MatchResultItem, value: number) {
  try {
    await setPriority('supplier', r.entity.id, value)
    priorities.value = { ...priorities.value, [r.entity.id]: value }
  } catch (e) {
    alert(errMsg(e))
  }
}

function scoreCls(score: number) {
  if (score >= 85) return 'bg-green-50 text-green-600'
  if (score >= 70) return 'bg-blue-50 text-blue-600'
  return 'bg-slate-100 text-slate-500'
}
function fmt(t: string | null) {
  return t ? t.replace('T', ' ').slice(0, 16) : '—'
}
const inputCls = 'w-full border border-line rounded-lg px-3.5 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20'
</script>

<template>
  <div class="space-y-5">
    <!-- 待我审批的详情申请 -->
    <div v-if="pendingReqs.length" class="bg-white rounded-xl border border-amber-200">
      <div class="px-5 py-3.5 border-b border-line text-sm font-bold text-amber-600">待我审批的详情查看申请</div>
      <div v-for="req in pendingReqs" :key="req.id" class="px-5 py-3.5 flex items-center gap-3 border-b border-line last:border-0">
        <div class="flex-1 text-[13px]">
          {{ userNames[req.requester_id] || `用户#${req.requester_id}` }} 申请查看你的{{ req.entity_type === 'supplier' ? '供货方' : '客户' }} #{{ req.entity_id }} 全量信息
          <span v-if="req.note" class="text-muted">(附言:{{ req.note }})</span>
        </div>
        <button class="px-5 py-2 rounded-lg text-[13px] bg-primary text-white" @click="respond(req, 'approve')">批准</button>
        <button class="px-5 py-2 rounded-lg text-[13px] border border-line text-muted" @click="respond(req, 'reject')">拒绝</button>
      </div>
    </div>

    <!-- 匹配面板 -->
    <div class="bg-white rounded-xl border border-line p-5">
      <div class="flex items-center gap-3 flex-wrap">
        <div class="flex gap-1 bg-slate-100 rounded-lg p-1">
          <button class="px-4 py-1.5 rounded-md text-[13px] transition" :class="sourceType === 'customer' ? 'bg-white shadow text-navy font-medium' : 'text-muted'" @click="sourceType = 'customer'">按我的客户</button>
          <button class="px-4 py-1.5 rounded-md text-[13px] transition" :class="sourceType === 'publication' ? 'bg-white shadow text-navy font-medium' : 'text-muted'" @click="sourceType = 'publication'">按我的需求发布</button>
        </div>
        <select v-if="sourceType === 'customer'" v-model="customerId" :class="inputCls + ' w-72'">
          <option v-for="c in customers" :key="c.id" :value="c.id">{{ c.name }}{{ c.intent_quantity ? `(意向 ${c.intent_quantity})` : '' }}</option>
        </select>
        <select v-else v-model="publicationId" :class="inputCls + ' w-72'">
          <option v-for="p in demandPubs" :key="p.id" :value="p.id">{{ p.title }}{{ p.quantity ? `(数量 ${p.quantity})` : '' }}</option>
        </select>
        <button :disabled="matching" class="px-6 py-2.5 rounded-lg text-sm bg-primary disabled:opacity-60 text-white transition" @click="doMatch">
          {{ matching ? '匹配中…' : '开始匹配' }}
        </button>
        <div class="text-xs text-muted">只匹配上游供货方;自己维护的数据全量显示,他人数据简要显示并可申请详情</div>
      </div>
      <p v-if="matchErr" class="text-[13px] text-red-500 mt-3">{{ matchErr }}</p>
    </div>

    <!-- 结果 -->
    <div v-if="results.length || filtered.length">
      <div v-if="filtered.length" class="bg-white rounded-xl border border-line p-4 mb-4">
        <div class="text-[13px] text-muted mb-2">被硬性条件过滤 {{ filtered.length }} 家:</div>
        <div class="flex flex-wrap gap-2">
          <span v-for="f in filtered" :key="f.supplier_id" class="text-xs px-2.5 py-1 rounded bg-slate-100 text-slate-500">{{ f.name }} · {{ f.reason }}</span>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div v-for="(r, idx) in results" :key="r.entity.id" class="bg-white rounded-xl border border-line p-5 hover:shadow-md transition">
          <div class="flex items-center gap-3 mb-2">
            <span class="text-sm font-bold px-2.5 py-1 rounded" :class="scoreCls(r.score)">匹配度 {{ r.score }}%</span>
            <span v-if="idx === 0" class="text-xs px-2 py-0.5 rounded bg-cyan-50 text-cyan-600">最佳匹配</span>
            <span class="text-xs px-2 py-0.5 rounded" :class="r.full ? 'bg-green-50 text-green-600' : 'bg-amber-50 text-amber-600'">{{ r.full ? '全量信息' : '简要信息' }}</span>
            <span v-if="!r.full" class="text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-600">{{ r.entity.owner_name }} 维护</span>
          </div>
          <div class="text-[15px] font-semibold">{{ r.entity.name }}<span v-if="r.entity.short_name" class="text-muted text-[13px] font-normal ml-2">{{ r.entity.short_name }}</span></div>
          <div class="text-[13px] text-muted mt-1.5">
            {{ r.entity.goods_type }} · 可用配额 {{ r.available_quantity }} · 报价 {{ r.entity.price != null ? `${r.entity.price.toLocaleString()} ${r.entity.currency}` : '—' }}
          </div>
          <template v-if="r.full">
            <div class="text-[13px] text-muted mt-1">
              采购方式:{{ (r.entity.procurement_modes || []).join(' / ') || '—' }} · 起订量:{{ r.entity.moq || '—' }} · 交货周期:{{ r.entity.delivery_cycle || '—' }}
            </div>
            <div v-if="r.entity.guarantee_type" class="text-[13px] text-muted mt-1">
              保障:{{ r.entity.guarantee_type }}{{ r.entity.guarantee_ratio ? ` ${r.entity.guarantee_ratio}` : '' }}{{ r.entity.guarantee_issuer_name ? ` · ${r.entity.guarantee_issuer_name}` : '' }}
            </div>
            <div v-if="r.entity.fulfillment_rate" class="text-[13px] text-muted mt-1">历史履约率:{{ r.entity.fulfillment_rate }}</div>
          </template>
          <details class="mt-3">
            <summary class="text-xs text-primary cursor-pointer select-none">为什么匹配?(评分依据)</summary>
            <ul class="text-xs text-muted mt-2 space-y-1 list-disc pl-4">
              <li v-for="reason in r.reasons" :key="reason">{{ reason }}</li>
              <li class="text-slate-400">优先级 {{ r.breakdown.priority }} · 时效 {{ r.breakdown.freshness }} · 偏好 {{ r.breakdown.preference }} · 价格 {{ r.breakdown.price }} · 信用 {{ r.breakdown.credit }}</li>
            </ul>
          </details>
          <div class="flex items-center gap-2 border-t border-line pt-3 mt-3">
            <div class="flex items-center gap-2">
              <span class="text-[13px] text-muted">我的优先级</span>
              <select :value="priorities[r.entity.id] ?? ''" :class="inputCls + ' !w-24 !py-1.5'" @change="quickPriority(r, Number(($event.target as HTMLSelectElement).value))">
                <option value="">默认(时间)</option>
                <option v-for="n in 9" :key="n" :value="n">{{ n }}</option>
              </select>
            </div>
            <button v-if="!r.full" class="ml-auto px-4 py-2 rounded-lg text-[13px] border border-primary text-primary transition" @click="requestFull(r)">申请查看详情</button>
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="matching === false && customers.length === 0 && demandPubs.length === 0" class="bg-white rounded-xl border border-line py-10 text-center text-muted text-[13px]">
      暂无需求来源:先在主体管理维护下游客户,或在供需看板发布采购需求
    </div>
  </div>
</template>
