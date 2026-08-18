<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import {
  createCommunication,
  createQuota,
  deleteQuota,
  listCommunications,
  listProductLines,
  listQuotas,
  updateQuota,
  type Chain,
  type Communication,
  type ProductLine,
  type Quota,
  type Supplier,
} from '../../api/entities'
import { errMsg } from '../../api/http'

const props = defineProps<{
  supplier: Supplier
  chains: Chain[]
  userNames: Record<number, string>
}>()
const emit = defineEmits<{ (e: 'close'): void }>()

const quotas = ref<Quota[]>([])
const comms = ref<Communication[]>([])
const products = ref<ProductLine[]>([])

async function loadAll() {
  quotas.value = await listQuotas(props.supplier.id).catch(() => [])
  comms.value = await listCommunications('supplier', props.supplier.id).catch(() => [])
}
onMounted(async () => {
  loadAll()
  products.value = await listProductLines().catch(() => [])
})

// ---------- 配额 ----------
const quotaDlg = reactive({ show: false, target: null as Quota | null })
const quotaForm = reactive({ product_line_id: null as number | null, batch_no: '', quantity: 0, used_quantity: 0, quota_start_at: '', quota_end_at: '', status: 'available', remark: '' })
const quotaErr = ref('')

function openQuota(q: Quota | null) {
  quotaDlg.target = q
  if (q) {
    Object.assign(quotaForm, {
      product_line_id: q.product_line_id, batch_no: q.batch_no, quantity: q.quantity,
      used_quantity: q.used_quantity, quota_start_at: q.quota_start_at || '', quota_end_at: q.quota_end_at || '',
      status: q.status, remark: q.remark,
    })
  } else {
    Object.assign(quotaForm, { product_line_id: null, batch_no: '', quantity: 0, used_quantity: 0, quota_start_at: '', quota_end_at: '', status: 'available', remark: '' })
  }
  quotaErr.value = ''
  quotaDlg.show = true
}

async function saveQuota() {
  quotaErr.value = ''
  try {
    const payload = {
      product_line_id: quotaForm.product_line_id,
      batch_no: quotaForm.batch_no,
      quantity: Number(quotaForm.quantity),
      used_quantity: Number(quotaForm.used_quantity),
      quota_start_at: quotaForm.quota_start_at || null,
      quota_end_at: quotaForm.quota_end_at || null,
      status: quotaForm.status,
      remark: quotaForm.remark,
    }
    if (quotaDlg.target) await updateQuota(quotaDlg.target.id, payload)
    else await createQuota(props.supplier.id, payload)
    quotaDlg.show = false
    loadAll()
  } catch (e) {
    quotaErr.value = errMsg(e)
  }
}

async function removeQuota(q: Quota) {
  if (!window.confirm(`确认删除配额「${q.batch_no || q.id}」?`)) return
  try {
    await deleteQuota(q.id)
    loadAll()
  } catch (e) {
    alert(errMsg(e))
  }
}

const quotaStatusMeta: Record<string, { label: string; cls: string }> = {
  available: { label: '可用', cls: 'bg-green-50 text-green-600' },
  locked: { label: '锁定', cls: 'bg-blue-50 text-blue-600' },
  used_up: { label: '用完', cls: 'bg-slate-100 text-slate-500' },
  expired: { label: '过期', cls: 'bg-red-50 text-red-600' },
}

// ---------- 沟通记录 ----------
const commDlg = reactive({ show: false })
const commForm = reactive({ comm_time: '', channel: '微信', participants: '', content: '', next_step: '', follow_up_at: '' })
const commErr = ref('')

async function saveComm() {
  commErr.value = ''
  if (!commForm.content.trim()) {
    commErr.value = '请填写沟通内容'
    return
  }
  try {
    await createCommunication('supplier', props.supplier.id, {
      comm_time: commForm.comm_time ? commForm.comm_time.replace('T', ' ') + ':00' : null,
      channel: commForm.channel,
      participants: commForm.participants,
      content: commForm.content,
      next_step: commForm.next_step,
      follow_up_at: commForm.follow_up_at ? commForm.follow_up_at.replace('T', ' ') + ':00' : null,
    })
    Object.assign(commForm, { comm_time: '', channel: '微信', participants: '', content: '', next_step: '', follow_up_at: '' })
    commDlg.show = false
    loadAll()
  } catch (e) {
    commErr.value = errMsg(e)
  }
}

const itemCls = 'bg-slate-50 rounded-lg px-3 py-2'
function fmt(t: string | null) {
  return t ? t.replace('T', ' ').slice(0, 16) : '—'
}
function pname(id: number | null) {
  return id == null ? '—' : products.value.find((p) => p.id === id)?.name || `#${id}`
}
const inputCls = 'w-full border border-line rounded-lg px-3.5 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20'
const labelCls = 'block text-[13px] text-muted mb-1.5'

const groups: { title: string; items: [string, unknown][] }[] = [
  {
    title: '基础信息',
    items: [
      ['名称', props.supplier.name],
      ['简称', props.supplier.short_name || '—'],
      ['注册地', props.supplier.reg_location || '—'],
      ['信用代码', props.supplier.credit_code || '—'],
      ['成立时间', props.supplier.established_at || '—'],
      ['注册资本', props.supplier.registered_capital || '—'],
      ['股权结构', props.supplier.equity_structure || '—'],
    ],
  },
  {
    title: '链路归属',
    items: [
      ['海外链路方', props.chains.find((c) => c.id === props.supplier.chain_id)?.name || '未标注'],
      ['链路角色', props.supplier.chain_role || '—'],
    ],
  },
  {
    title: '交易属性',
    items: [
      ['采购方式', (props.supplier.procurement_modes || []).join(' / ') || '—'],
      ['期货/现货', props.supplier.goods_type],
      ['报价', props.supplier.price != null ? `${props.supplier.price.toLocaleString()} ${props.supplier.currency}` : '—'],
      ['报价有效期', props.supplier.price_valid_until || '—'],
      ['起订量', props.supplier.moq || '—'],
      ['交货周期', props.supplier.delivery_cycle || '—'],
      ['付款节点', props.supplier.payment_terms || '—'],
    ],
  },
  {
    title: '反向保障',
    items: [
      ['保障措施', props.supplier.guarantee_type || '—'],
      ['保函比例', props.supplier.guarantee_ratio || '—'],
      ['开具方', [props.supplier.guarantee_issuer, props.supplier.guarantee_issuer_name].filter(Boolean).join(' · ') || '—'],
      ['保障有效期', props.supplier.guarantee_valid_until || '—'],
      ['垫资能力', props.supplier.financing_capacity || '—'],
    ],
  },
  {
    title: '合作评价',
    items: [
      ['合作状态', props.supplier.coop_status],
      ['成交次数', String(props.supplier.deal_count)],
      ['履约率', props.supplier.fulfillment_rate || '—'],
      ['信用评级', props.supplier.credit_rating || '—'],
      ['风险备注', props.supplier.risk_notes || '—'],
    ],
  },
]
</script>

<template>
  <div class="fixed inset-0 bg-black/40 z-40" @click.self="emit('close')"></div>
  <div class="fixed inset-y-0 right-0 w-[720px] max-w-[92vw] bg-white shadow-2xl z-50 flex flex-col">
    <div class="px-6 py-4 border-b border-line flex items-center shrink-0">
      <div>
        <div class="text-sm font-bold">{{ supplier.name }}</div>
        <div class="text-xs text-muted">最后维护:{{ userNames[supplier.last_editor_id!] || '—' }} · {{ fmt(supplier.updated_at) }} · 版本 v{{ supplier.version }}</div>
      </div>
      <button class="ml-auto text-xl text-muted hover:text-navy" @click="emit('close')">×</button>
    </div>
    <div class="flex-1 overflow-y-auto p-6">
      <div v-for="g in groups" :key="g.title" class="mb-5">
        <div class="text-[13px] font-bold text-primary mb-2">{{ g.title }}</div>
        <div class="grid grid-cols-2 gap-2">
          <div v-for="[k, v] in g.items" :key="k" :class="itemCls">
            <div class="text-xs text-muted">{{ k }}</div>
            <div class="text-sm mt-0.5 break-all">{{ v }}</div>
          </div>
        </div>
      </div>

      <!-- 批次配额 -->
      <div class="flex items-center justify-between mt-6 mb-2">
        <div class="text-[13px] font-bold text-primary">批次配额</div>
        <button class="px-3 py-1.5 rounded-lg text-[13px] bg-primary text-white" @click="openQuota(null)">+ 新增配额</button>
      </div>
      <table class="w-full text-[13px] border border-line rounded-lg overflow-hidden">
        <thead>
          <tr class="bg-slate-50 text-muted text-left">
            <th class="px-3 py-2 font-medium">批次号</th>
            <th class="px-3 py-2 font-medium">产品线</th>
            <th class="px-3 py-2 font-medium">数量</th>
            <th class="px-3 py-2 font-medium">有效期</th>
            <th class="px-3 py-2 font-medium">状态</th>
            <th class="px-3 py-2 font-medium text-right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!quotas.length"><td colspan="6" class="px-3 py-4 text-center text-muted">暂无配额批次</td></tr>
          <tr v-for="q in quotas" :key="q.id" class="border-t border-line">
            <td class="px-3 py-2 font-medium">{{ q.batch_no || `#${q.id}` }}</td>
            <td class="px-3 py-2 text-muted">{{ pname(q.product_line_id) }}</td>
            <td class="px-3 py-2" style="font-variant-numeric: tabular-nums">{{ q.quantity }}{{ q.used_quantity ? `(已用${q.used_quantity})` : '' }}</td>
            <td class="px-3 py-2 text-muted">{{ q.quota_start_at || '?' }} ~ {{ q.quota_end_at || '?' }}</td>
            <td class="px-3 py-2"><span class="text-xs px-1.5 py-0.5 rounded" :class="quotaStatusMeta[q.status]?.cls">{{ quotaStatusMeta[q.status]?.label || q.status }}</span></td>
            <td class="px-3 py-2 text-right whitespace-nowrap">
              <button class="text-[13px] text-primary hover:underline mr-2" @click="openQuota(q)">编辑</button>
              <button class="text-[13px] text-red-500 hover:underline" @click="removeQuota(q)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- 沟通记录 -->
      <div class="flex items-center justify-between mt-6 mb-2">
        <div class="text-[13px] font-bold text-primary">沟通记录(只增不改)</div>
        <button class="px-3 py-1.5 rounded-lg text-[13px] bg-primary text-white" @click="commDlg.show = true">+ 记录沟通</button>
      </div>
      <div class="border-l-2 border-line pl-4 space-y-3">
        <div v-if="!comms.length" class="text-[13px] text-muted py-2">暂无沟通记录</div>
        <div v-for="c in comms" :key="c.id" class="bg-white border border-line rounded-lg p-3">
          <div class="flex items-center gap-2 text-xs text-muted mb-1">
            <span class="px-1.5 py-0.5 rounded bg-slate-100">{{ c.channel || '—' }}</span>
            <span>{{ fmt(c.comm_time) }}</span>
            <span>·</span>
            <span>{{ c.created_by_name }}</span>
          </div>
          <div class="text-[13px] whitespace-pre-wrap">{{ c.content }}</div>
          <div v-if="c.next_step" class="text-xs text-primary mt-1">下一步:{{ c.next_step }}</div>
        </div>
      </div>
    </div>

    <!-- 配额弹窗 -->
    <div v-if="quotaDlg.show" class="fixed inset-0 bg-black/40 flex items-center justify-center z-[60]" @click.self="quotaDlg.show = false">
      <div class="bg-white rounded-xl w-[420px] p-6 shadow-2xl">
        <div class="text-base font-bold mb-4">{{ quotaDlg.target ? '编辑配额' : '新增配额' }}</div>
        <div class="grid grid-cols-2 gap-3">
          <div><label :class="labelCls">产品型号</label><select v-model="quotaForm.product_line_id" :class="inputCls"><option :value="null">未选择</option><option v-for="p in products" :key="p.id" :value="p.id">{{ p.name }}</option></select></div>
          <div><label :class="labelCls">批次号</label><input v-model="quotaForm.batch_no" :class="inputCls" /></div>
          <div><label :class="labelCls">配额数量</label><input v-model="quotaForm.quantity" type="number" :class="inputCls" /></div>
          <div><label :class="labelCls">已用数量</label><input v-model="quotaForm.used_quantity" type="number" :class="inputCls" /></div>
          <div><label :class="labelCls">产生时间</label><input v-model="quotaForm.quota_start_at" type="date" :class="inputCls" /></div>
          <div><label :class="labelCls">结束时间</label><input v-model="quotaForm.quota_end_at" type="date" :class="inputCls" /></div>
          <div><label :class="labelCls">状态</label><select v-model="quotaForm.status" :class="inputCls"><option v-for="(m, k) in quotaStatusMeta" :key="k" :value="k">{{ m.label }}</option></select></div>
          <div><label :class="labelCls">备注</label><input v-model="quotaForm.remark" :class="inputCls" /></div>
        </div>
        <p v-if="quotaErr" class="text-[13px] text-red-500 mt-3">{{ quotaErr }}</p>
        <div class="flex justify-end gap-2 mt-5">
          <button class="px-5 py-2.5 rounded-lg text-[13px] border border-line text-muted" @click="quotaDlg.show = false">取消</button>
          <button class="px-5 py-2.5 rounded-lg text-[13px] bg-primary text-white" @click="saveQuota">保存</button>
        </div>
      </div>
    </div>

    <!-- 沟通弹窗 -->
    <div v-if="commDlg.show" class="fixed inset-0 bg-black/40 flex items-center justify-center z-[60]" @click.self="commDlg.show = false">
      <div class="bg-white rounded-xl w-[460px] p-6 shadow-2xl">
        <div class="text-base font-bold mb-4">记录沟通</div>
        <div class="grid grid-cols-2 gap-3">
          <div><label :class="labelCls">沟通时间</label><input v-model="commForm.comm_time" type="datetime-local" :class="inputCls" /></div>
          <div><label :class="labelCls">沟通方式</label><select v-model="commForm.channel" :class="inputCls"><option v-for="c in ['电话', '微信', '面谈', '会议', '其他']" :key="c" :value="c">{{ c }}</option></select></div>
          <div class="col-span-2"><label :class="labelCls">参与人</label><input v-model="commForm.participants" :class="inputCls" /></div>
          <div class="col-span-2"><label :class="labelCls">沟通内容 *</label><textarea v-model="commForm.content" :class="inputCls" rows="4"></textarea></div>
          <div class="col-span-2"><label :class="labelCls">下一步计划</label><input v-model="commForm.next_step" :class="inputCls" /></div>
          <div class="col-span-2"><label :class="labelCls">跟进时间</label><input v-model="commForm.follow_up_at" type="datetime-local" :class="inputCls" /></div>
        </div>
        <p v-if="commErr" class="text-[13px] text-red-500 mt-3">{{ commErr }}</p>
        <div class="flex justify-end gap-2 mt-5">
          <button class="px-5 py-2.5 rounded-lg text-[13px] border border-line text-muted" @click="commDlg.show = false">取消</button>
          <button class="px-5 py-2.5 rounded-lg text-[13px] bg-primary text-white" @click="saveComm">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>
