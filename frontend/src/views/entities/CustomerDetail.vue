<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  createCommunication,
  createVerification,
  deleteVerification,
  listCommunications,
  listVerifications,
  reviewVerification,
  uploadFile,
  type Communication,
  type Customer,
  type Verification,
} from '../../api/entities'
import { errMsg } from '../../api/http'
import { useAuthStore } from '../../stores/auth'

const props = defineProps<{ customer: Customer; userNames: Record<number, string> }>()
const emit = defineEmits<{ (e: 'close'): void }>()

const auth = useAuthStore()
const vers = ref<Verification[]>([])
const comms = ref<Communication[]>([])

async function loadAll() {
  vers.value = await listVerifications(props.customer.id).catch(() => [])
  comms.value = await listCommunications('customer', props.customer.id).catch(() => [])
}
onMounted(loadAll)

const typeMeta: Record<string, { label: string; valid: string }> = {
  video: { label: '视频验资', valid: '3 日内录制' },
  balance_photo: { label: '账户余额照片', valid: '需体现日期,3 日内' },
  bank_certificate: { label: '银行资信证明', valid: '1 个月内开具' },
  guarantee_letter: { label: '上级控股方担保证明', valid: '按担保函期限' },
}
const reviewMeta: Record<string, { label: string; cls: string }> = {
  pending: { label: '待终审', cls: 'bg-amber-50 text-amber-600' },
  approved: { label: '已通过', cls: 'bg-green-50 text-green-600' },
  rejected: { label: '已驳回', cls: 'bg-red-50 text-red-600' },
}
const aiMeta: Record<string, { label: string; cls: string }> = {
  pending: { label: 'AI 待初审', cls: 'bg-slate-100 text-slate-500' },
  passed: { label: 'AI 通过', cls: 'bg-blue-50 text-blue-600' },
  flagged: { label: 'AI 存疑', cls: 'bg-amber-50 text-amber-600' },
}

// ---------- 验资上传 ----------
const vDlg = reactive({ show: false })
const vForm = reactive({ verify_type: 'balance_photo', material_date: '', amount: '', file: null as File | null })
const vErr = ref('')
const uploading = ref(false)

async function saveVerification() {
  vErr.value = ''
  if (!vForm.file) {
    vErr.value = '请选择材料文件(图片/PDF/视频)'
    return
  }
  uploading.value = true
  try {
    const up = await uploadFile(vForm.file, 'customer', props.customer.id)
    let validUntil: string | null = null
    if (vForm.material_date) {
      const d = new Date(vForm.material_date)
      const days = vForm.verify_type === 'bank_certificate' ? 30 : vForm.verify_type === 'guarantee_letter' ? null : 3
      if (days) {
        d.setDate(d.getDate() + days)
        validUntil = d.toISOString().slice(0, 10)
      }
    }
    await createVerification(props.customer.id, {
      verify_type: vForm.verify_type,
      file_name: up.original_name,
      file_path: up.stored_name,
      material_date: vForm.material_date || null,
      valid_until: validUntil,
      amount: vForm.amount,
    })
    Object.assign(vForm, { verify_type: 'balance_photo', material_date: '', amount: '', file: null })
    vDlg.show = false
    loadAll()
  } catch (e) {
    vErr.value = errMsg(e)
  } finally {
    uploading.value = false
  }
}

function onFilePicked(e: Event) {
  vForm.file = (e.target as HTMLInputElement).files?.[0] || null
}

async function doReview(v: Verification, status: 'approved' | 'rejected') {
  const note = window.prompt(status === 'approved' ? '终审通过,备注(可留空):' : '终审驳回,请填写原因:') || ''
  try {
    await reviewVerification(v.id, status, note)
    loadAll()
  } catch (e) {
    alert(errMsg(e))
  }
}
async function removeV(v: Verification) {
  if (!window.confirm('确认删除该验资材料?')) return
  try {
    await deleteVerification(v.id)
    loadAll()
  } catch (e) {
    alert(errMsg(e))
  }
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
    await createCommunication('customer', props.customer.id, {
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

const inputCls = 'w-full border border-line rounded-lg px-3.5 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20'
const labelCls = 'block text-[13px] text-muted mb-1.5'
const itemCls = 'bg-slate-50 rounded-lg px-3 py-2'
function fmt(t: string | null) {
  return t ? t.replace('T', ' ').slice(0, 16) : '—'
}
function isExpired(v: Verification) {
  return v.valid_until != null && v.valid_until < new Date().toISOString().slice(0, 10)
}

const groups: { title: string; items: [string, unknown][] }[] = [
  {
    title: '基础信息',
    items: [
      ['采购主体', props.customer.name],
      ['信用代码', props.customer.credit_code || '—'],
      ['注册地', props.customer.reg_location || '—'],
      ['成立时间', props.customer.established_at || '—'],
      ['注册资本', props.customer.registered_capital || '—'],
      ['行业', props.customer.industry || '—'],

    ],
  },
  {
    title: '开票信息',
    items: [
      ['单位全称', props.customer.invoice_detail?.单位全称 || '—'],
      ['开户行', props.customer.invoice_detail?.开户行 || '—'],
      ['行号/账号', props.customer.invoice_detail?.账号 || '—'],
      ['地址', props.customer.invoice_detail?.地址 || '—'],
      ['联系人', props.customer.invoice_detail?.联系人 || '—'],
      ['联系方式', props.customer.invoice_detail?.联系方式 || '—'],
    ],
  },
  {
    title: '交易意向',
    items: [
      ['意向方式', (props.customer.intent_modes || []).join(' / ') || '—'],
      ['现货/期货', props.customer.goods_preference || '—'],
      ['意向数量', props.customer.intent_quantity || '—'],
      ['预算区间', props.customer.budget_range || '—'],
      ['预期成交', props.customer.expected_deal_at || '—'],
    ],
  },
  {
    title: '客户画像',
    items: [
      ['客户类型', props.customer.customer_type || '—'],
      ['采购用途', props.customer.purpose || '—'],
      ['价值分级', props.customer.value_grade ? `${props.customer.value_grade} 级` : '—'],
      ['付款习惯', props.customer.payment_habit || '—'],
      ['风险偏好', props.customer.risk_preference || '—'],
      ['决策链', props.customer.decision_chain || '—'],
    ],
  },
]
</script>

<template>
  <div class="fixed inset-0 bg-black/40 z-40" @click.self="emit('close')"></div>
  <div class="fixed inset-y-0 right-0 w-[720px] max-w-[92vw] bg-white shadow-2xl z-50 flex flex-col">
    <div class="px-6 py-4 border-b border-line flex items-center shrink-0">
      <div>
        <div class="text-sm font-bold">{{ customer.name }}</div>
        <div class="text-xs text-muted">最后维护:{{ userNames[customer.last_editor_id!] || '—' }} · {{ fmt(customer.updated_at) }} · 版本 v{{ customer.version }}</div>
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

      <!-- 验资材料 -->
      <div class="flex items-center justify-between mt-6 mb-2">
        <div class="text-[13px] font-bold text-primary">验资材料(四种方式,可多选组合)</div>
        <button class="px-3 py-1.5 rounded-lg text-[13px] bg-primary text-white" @click="vDlg.show = true">+ 上传材料</button>
      </div>
      <table class="w-full text-[13px] border border-line rounded-lg overflow-hidden">
        <thead>
          <tr class="bg-slate-50 text-muted text-left">
            <th class="px-3 py-2 font-medium">方式</th>
            <th class="px-3 py-2 font-medium">材料日期</th>
            <th class="px-3 py-2 font-medium">有效期至</th>
            <th class="px-3 py-2 font-medium">金额</th>
            <th class="px-3 py-2 font-medium">AI 初审</th>
            <th class="px-3 py-2 font-medium">终审</th>
            <th class="px-3 py-2 font-medium text-right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!vers.length"><td colspan="7" class="px-3 py-4 text-center text-muted">暂无验资材料,上传后自动进入 AI 初审</td></tr>
          <tr v-for="v in vers" :key="v.id" class="border-t border-line">
            <td class="px-3 py-2 font-medium">{{ typeMeta[v.verify_type]?.label || v.verify_type }}</td>
            <td class="px-3 py-2 text-muted">{{ v.material_date || '—' }}</td>
            <td class="px-3 py-2">
              <span v-if="v.valid_until">{{ v.valid_until }}</span>
              <span v-if="isExpired(v)" class="ml-1 text-xs px-1.5 py-0.5 rounded bg-red-50 text-red-600">已过期</span>
            </td>
            <td class="px-3 py-2" style="font-variant-numeric: tabular-nums">{{ v.amount || '—' }}</td>
            <td class="px-3 py-2"><span class="text-xs px-1.5 py-0.5 rounded" :class="aiMeta[v.ai_status]?.cls">{{ aiMeta[v.ai_status]?.label || v.ai_status }}</span></td>
            <td class="px-3 py-2"><span class="text-xs px-1.5 py-0.5 rounded" :class="reviewMeta[v.review_status]?.cls">{{ reviewMeta[v.review_status]?.label }}</span></td>
            <td class="px-3 py-2 text-right whitespace-nowrap">
              <button v-if="v.review_status === 'pending'" class="text-[13px] text-green-600 hover:underline mr-2" @click="doReview(v, 'approved')">通过</button>
              <button v-if="v.review_status === 'pending'" class="text-[13px] text-red-500 hover:underline mr-2" @click="doReview(v, 'rejected')">驳回</button>
              <a v-if="v.file_path" :href="`/api/files/${v.file_path}`" target="_blank" class="text-[13px] text-primary hover:underline mr-2">查看</a>
              <button class="text-[13px] text-red-500 hover:underline" @click="removeV(v)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div class="text-xs text-muted mt-1.5">材料高度敏感:仅数据主人、共享范围内用户与管理员可见,下载全程留痕。</div>

      <!-- 沟通记录 -->
      <div class="flex items-center justify-between mt-6 mb-2">
        <div class="text-[13px] font-bold text-primary">沟通记录(只增不改,全程留痕)</div>
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

    <!-- 验资上传弹窗 -->
    <div v-if="vDlg.show" class="fixed inset-0 bg-black/40 flex items-center justify-center z-[60]" @click.self="vDlg.show = false">
      <div class="bg-white rounded-xl w-[440px] p-6 shadow-2xl">
        <div class="text-base font-bold mb-4">上传验资材料</div>
        <div class="grid gap-3">
          <div>
            <label :class="labelCls">验资方式 *</label>
            <select v-model="vForm.verify_type" :class="inputCls">
              <option v-for="(m, k) in typeMeta" :key="k" :value="k">{{ m.label }}({{ m.valid }})</option>
            </select>
          </div>
          <div><label :class="labelCls">材料日期(视频拍摄日/照片日期/开具日)</label><input v-model="vForm.material_date" type="date" :class="inputCls" /></div>
          <div><label :class="labelCls">验资金额(识别值)</label><input v-model="vForm.amount" :class="inputCls" /></div>
          <div>
            <label :class="labelCls">材料文件 *(图片/PDF/视频 ≤200MB)</label>
            <input type="file" accept=".jpg,.jpeg,.png,.webp,.pdf,.mp4,.mov" :class="inputCls" @change="onFilePicked" />
          </div>
        </div>
        <p v-if="vErr" class="text-[13px] text-red-500 mt-3">{{ vErr }}</p>
        <div class="flex justify-end gap-2 mt-5">
          <button class="px-5 py-2.5 rounded-lg text-[13px] border border-line text-muted" @click="vDlg.show = false">取消</button>
          <button :disabled="uploading" class="px-5 py-2.5 rounded-lg text-[13px] bg-primary disabled:opacity-60 text-white" @click="saveVerification">
            {{ uploading ? '上传中…' : '上传' }}
          </button>
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
