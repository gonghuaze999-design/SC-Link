<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import {
  createCustomer,
  deleteCustomer,
  listCustomers,
  listUserOptions,
  updateCustomer,
  type Customer,
} from '../../api/entities'
import { errMsg } from '../../api/http'
import CustomerDetail from './CustomerDetail.vue'

const rows = ref<Customer[]>([])
const userNames = ref<Record<number, string>>({})
const keyword = ref('')
const verified = ref('')
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    rows.value = await listCustomers({ keyword: keyword.value, verified: verified.value })
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

const dialog = reactive({ show: false, mode: 'create' as 'create' | 'edit', target: null as Customer | null })
const form = reactive<Record<string, any>>({})
const formError = ref('')

function blank(): Record<string, any> {
  return {
    name: '', credit_code: '', reg_location: '', established_at: null, registered_capital: '',
    industry: '', contacts: [], remark: '', invoice_info: '',
    intent_modes: [], intent_products: [], intent_quantity: '', budget_range: '',
    expected_deal_at: null, goods_preference: '',
    customer_type: '', purpose: '', decision_chain: '', payment_habit: '',
    risk_preference: '', value_grade: '', tags: [],
  }
}
function openCreate() {
  dialog.mode = 'create'
  dialog.target = null
  Object.assign(form, blank())
  formError.value = ''
  dialog.show = true
}
function openEdit(c: Customer) {
  dialog.mode = 'edit'
  dialog.target = c
  const b = blank()
  for (const k of Object.keys(b)) form[k] = (c as unknown as Record<string, unknown>)[k] ?? b[k]
  formError.value = ''
  dialog.show = true
}

const modeOptions = ['预付款', '信用证-国内', '信用证-跨境']
function toggleMode(m: string) {
  const arr = (form.intent_modes as string[]) || []
  form.intent_modes = arr.includes(m) ? arr.filter((x) => x !== m) : [...arr, m]
}

async function submit() {
  formError.value = ''
  try {
    if (dialog.mode === 'create') await createCustomer(form as Partial<Customer>)
    else if (dialog.target) await updateCustomer(dialog.target.id, { ...form, version: dialog.target.version } as Partial<Customer> & { version: number })
    dialog.show = false
    load()
  } catch (e) {
    formError.value = errMsg(e)
  }
}
async function remove(c: Customer) {
  if (!window.confirm(`确认删除客户「${c.name}」?其验资材料与沟通记录将一并删除,操作写入审计日志。`)) return
  try {
    await deleteCustomer(c.id)
    load()
  } catch (e) {
    alert(errMsg(e))
  }
}

const detail = ref<Customer | null>(null)
const customerTypes = ['终端使用方', '贸易商', '国资平台', '民营']
const grades = ['A', 'B', 'C']

const inputCls = 'w-full border border-line rounded-lg px-3.5 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20'
const labelCls = 'block text-[13px] text-muted mb-1.5'
function fmt(t: string | null) {
  return t ? t.replace('T', ' ').slice(0, 16) : '—'
}
function editorName(id: number | null) {
  if (id == null) return '—'
  return userNames.value[id] || `用户#${id}`
}
</script>

<template>
  <div>
    <div class="bg-white rounded-xl border border-line">
      <div class="flex items-center gap-3 p-4 border-b border-line">
        <input v-model="keyword" :class="inputCls + ' w-56'" placeholder="搜索客户名称" @keyup.enter="load" />
        <select v-model="verified" :class="inputCls + ' w-36'" @change="load">
          <option value="">全部客户</option>
          <option value="yes">已验资</option>
          <option value="no">未验资</option>
        </select>
        <button class="px-5 py-2.5 rounded-lg text-[13px] border border-line text-muted hover:bg-slate-50 transition" @click="load">搜索</button>
        <button class="ml-auto px-5 py-2.5 rounded-lg text-[13px] bg-primary text-white transition whitespace-nowrap shrink-0" @click="openCreate">+ 新增客户</button>
      </div>
      <table class="w-full text-sm">
        <thead>
          <tr class="text-left text-muted text-[13px] border-b border-line">
            <th class="px-5 py-3.5 font-medium">采购主体</th>
            <th class="px-5 py-3.5 font-medium">类型</th>
            <th class="px-5 py-3.5 font-medium">意向采购方式</th>
            <th class="px-5 py-3.5 font-medium">意向数量</th>
            <th class="px-5 py-3.5 font-medium">验资</th>
            <th class="px-5 py-3.5 font-medium">等级</th>
            <th class="px-5 py-3.5 font-medium">维护人/更新</th>
            <th class="px-5 py-3.5 font-medium text-right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading"><td colspan="8" class="px-4 py-8 text-center text-muted">加载中…</td></tr>
          <tr v-else-if="!rows.length"><td colspan="8" class="px-4 py-8 text-center text-muted">暂无客户,点击右上角新增</td></tr>
          <tr v-for="c in rows" :key="c.id" class="border-b border-line hover:bg-slate-50/60 transition">
            <td class="px-5 py-3.5 font-medium">{{ c.name }}</td>
            <td class="px-5 py-3.5 text-muted">{{ c.customer_type || '—' }}</td>
            <td class="px-5 py-3.5 text-muted">{{ (c.intent_modes || []).join(' / ') || '—' }}</td>
            <td class="px-5 py-3.5 text-muted">{{ c.intent_quantity || '—' }}</td>
            <td class="px-5 py-3.5">
              <span class="text-xs px-2 py-0.5 rounded" :class="c.verified ? 'bg-green-50 text-green-600' : 'bg-amber-50 text-amber-600'">{{ c.verified ? '已验资' : '未验资' }}</span>
            </td>
            <td class="px-5 py-3.5">
              <span v-if="c.value_grade" class="text-xs px-2 py-0.5 rounded bg-blue-50 text-blue-600">{{ c.value_grade }} 级</span>
              <span v-else class="text-muted">—</span>
            </td>
            <td class="px-5 py-3.5 text-muted text-[13px]">{{ editorName(c.last_editor_id) }}<br>{{ fmt(c.updated_at) }}</td>
            <td class="px-5 py-3.5 text-right whitespace-nowrap">
              <button class="text-[13px] text-primary hover:underline mr-3" @click="detail = c">详情</button>
              <button class="text-[13px] text-primary hover:underline mr-3" @click="openEdit(c)">编辑</button>
              <button class="text-[13px] text-red-500 hover:underline" @click="remove(c)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="dialog.show" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50" @click.self="dialog.show = false">
      <div class="bg-white rounded-xl w-[720px] max-h-[86vh] overflow-y-auto shadow-2xl">
        <div class="px-6 py-4 border-b border-line sticky top-0 bg-white rounded-t-xl z-10">
          <div class="text-sm font-bold">{{ dialog.mode === 'create' ? '新增客户' : `编辑:${dialog.target?.name}` }}</div>
        </div>
        <div class="p-6 grid grid-cols-2 gap-4">
          <div class="col-span-2 text-[13px] font-bold text-primary pt-1">基础信息</div>
          <div><label :class="labelCls">采购主体名称 *</label><input v-model="form.name" :class="inputCls" /></div>
          <div><label :class="labelCls">统一社会信用代码</label><input v-model="form.credit_code" :class="inputCls" /></div>
          <div><label :class="labelCls">注册地</label><input v-model="form.reg_location" :class="inputCls" /></div>
          <div><label :class="labelCls">行业</label><input v-model="form.industry" :class="inputCls" /></div>
          <div><label :class="labelCls">成立时间</label><input v-model="form.established_at" type="date" :class="inputCls" /></div>
          <div><label :class="labelCls">注册资本</label><input v-model="form.registered_capital" :class="inputCls" /></div>
          <div class="col-span-2"><label :class="labelCls">开票信息</label><input v-model="form.invoice_info" :class="inputCls" /></div>

          <div class="col-span-2 text-[13px] font-bold text-primary pt-2">交易意向</div>
          <div>
            <label :class="labelCls">意向采购方式(可多选)</label>
            <div class="flex gap-2">
              <button v-for="m in modeOptions" :key="m" type="button" class="px-3 py-1.5 rounded-lg text-[13px] border transition" :class="((form.intent_modes as string[]) || []).includes(m) ? 'border-primary bg-blue-50 text-primary' : 'border-line text-muted hover:border-slate-400'" @click="toggleMode(m)">{{ m }}</button>
            </div>
          </div>
          <div><label :class="labelCls">现货/期货偏好</label><select v-model="form.goods_preference" :class="inputCls"><option value="">未设置</option><option value="现货">现货</option><option value="期货">期货</option></select></div>
          <div><label :class="labelCls">意向数量</label><input v-model="form.intent_quantity" :class="inputCls" /></div>
          <div><label :class="labelCls">预算区间</label><input v-model="form.budget_range" :class="inputCls" /></div>
          <div><label :class="labelCls">预期成交时间</label><input v-model="form.expected_deal_at" type="date" :class="inputCls" /></div>

          <div class="col-span-2 text-[13px] font-bold text-primary pt-2">客户画像</div>
          <div><label :class="labelCls">客户类型</label><select v-model="form.customer_type" :class="inputCls"><option value="">未设置</option><option v-for="t in customerTypes" :key="t" :value="t">{{ t }}</option></select></div>
          <div><label :class="labelCls">采购用途</label><select v-model="form.purpose" :class="inputCls"><option value="">未设置</option><option value="自用">自用</option><option value="转售">转售</option></select></div>
          <div><label :class="labelCls">客户价值分级</label><select v-model="form.value_grade" :class="inputCls"><option value="">未设置</option><option v-for="g in grades" :key="g" :value="g">{{ g }} 级</option></select></div>
          <div><label :class="labelCls">付款习惯</label><input v-model="form.payment_habit" :class="inputCls" /></div>
          <div><label :class="labelCls">风险偏好</label><input v-model="form.risk_preference" :class="inputCls" /></div>
          <div><label :class="labelCls">决策链</label><input v-model="form.decision_chain" :class="inputCls" /></div>
          <div class="col-span-2"><label :class="labelCls">备注</label><textarea v-model="form.remark" :class="inputCls" rows="2"></textarea></div>
        </div>
        <div class="px-6 py-4 border-t border-line flex items-center justify-end gap-2 sticky bottom-0 bg-white rounded-b-xl">
          <p v-if="formError" class="text-[13px] text-red-500 mr-auto">{{ formError }}</p>
          <button class="px-5 py-2.5 rounded-lg text-[13px] border border-line text-muted hover:bg-slate-50 transition" @click="dialog.show = false">取消</button>
          <button class="px-5 py-2.5 rounded-lg text-[13px] bg-primary text-white transition" @click="submit">保存</button>
        </div>
      </div>
    </div>

    <CustomerDetail v-if="detail" :customer="detail" :user-names="userNames" @close="detail = null; load()" />
  </div>
</template>
