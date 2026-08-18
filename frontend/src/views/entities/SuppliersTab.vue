<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import {
  createSupplier,
  deleteSupplier,
  listChains,
  listSuppliers,
  listUserOptions,
  updateSupplier,
  type Chain,
  type Supplier,
} from '../../api/entities'
import { errMsg } from '../../api/http'
import { listPriorities, setPriority } from '../../api/match'
import SupplierDetail from './SupplierDetail.vue'

const rows = ref<Supplier[]>([])
const chains = ref<Chain[]>([])
const userNames = ref<Record<number, string>>({})
const priorities = ref<Record<number, number>>({})
const keyword = ref('')
const goodsType = ref('')
const chainFilter = ref<number | ''>('')
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    rows.value = await listSuppliers({
      keyword: keyword.value,
      goods_type: goodsType.value,
      chain_id: chainFilter.value === '' ? undefined : chainFilter.value,
    })
  } catch (e) {
    alert(errMsg(e))
  } finally {
    loading.value = false
  }
}
async function loadPriorities() {
  const prs = await listPriorities().catch(() => [])
  priorities.value = Object.fromEntries(prs.filter((p) => p.entity_type === 'supplier').map((p) => [p.entity_id, p.priority]))
}
async function quickPriority(s: Supplier, value: number) {
  try {
    await setPriority('supplier', s.id, value)
    loadPriorities()
  } catch (e) {
    alert(errMsg(e))
  }
}
onMounted(async () => {
  load()
  loadPriorities()
  chains.value = await listChains().catch(() => [])
  userNames.value = Object.fromEntries((await listUserOptions().catch(() => [])).map((u) => [u.id, u.display_name || u.username]))
})

const dialog = reactive({ show: false, mode: 'create' as 'create' | 'edit', target: null as Supplier | null })
const form = reactive<Record<string, any>>({})
const formError = ref('')

function blank(): Record<string, any> {
  return {
    name: '', short_name: '', reg_location: '', credit_code: '', established_at: null,
    registered_capital: '', equity_structure: '', contacts: [], remark: '',
    chain_id: null, chain_role: '', parent_supplier_id: null,
    procurement_modes: [], goods_type: '现货', price: null, currency: 'CNY', price_valid_until: null,
    moq: '', delivery_cycle: '', payment_terms: '', invoice_type: '',
    guarantee_type: '', guarantee_ratio: '', guarantee_issuer: '', guarantee_issuer_name: '',
    guarantee_valid_until: null, financing_capacity: '', guarantee_notes: '',
    coop_status: '意向', deal_count: 0, deal_amount: null, fulfillment_rate: '',
    breach_count: 0, credit_rating: '', risk_notes: '',
  }
}

function openCreate() {
  dialog.mode = 'create'
  dialog.target = null
  Object.assign(form, blank())
  formError.value = ''
  dialog.show = true
}
function openEdit(s: Supplier) {
  dialog.mode = 'edit'
  dialog.target = s
  const b = blank()
  for (const k of Object.keys(b)) form[k] = (s as unknown as Record<string, unknown>)[k] ?? b[k]
  formError.value = ''
  dialog.show = true
}

const modeOptions = ['预付款', '信用证-国内', '信用证-跨境']
function toggleMode(m: string) {
  const arr = (form.procurement_modes as string[]) || []
  form.procurement_modes = arr.includes(m) ? arr.filter((x) => x !== m) : [...arr, m]
}

async function submit() {
  formError.value = ''
  const payload = { ...form }
  try {
    if (dialog.mode === 'create') {
      await createSupplier(payload as Partial<Supplier>)
    } else if (dialog.target) {
      await updateSupplier(dialog.target.id, { ...payload, version: dialog.target.version } as Partial<Supplier> & { version: number })
    }
    dialog.show = false
    load()
  } catch (e) {
    formError.value = errMsg(e)
  }
}

async function remove(s: Supplier) {
  if (!window.confirm(`确认删除供货方「${s.name}」?其配额将一并删除,操作写入审计日志。`)) return
  try {
    await deleteSupplier(s.id)
    load()
  } catch (e) {
    alert(errMsg(e))
  }
}

const detail = ref<Supplier | null>(null)
function openDetail(s: Supplier) {
  detail.value = s
}
function onDetailClosed() {
  detail.value = null
  load()
}

const goodsTypes = ['现货', '准现货', '期货']
const chainRoles = ['一手', '二手', '居间代表', '其他']
const guaranteeTypes = ['保函', '先开后开', '无', '其他']
const guaranteeIssuers = ['企业', '银行', '保险公司']
const coopStatuses = ['意向', '洽谈中', '合作中', '暂停', '终止']

function chainName(id: number | null) {
  if (id == null) return '未标注'
  return chains.value.find((c) => c.id === id)?.name || `链路#${id}`
}
function fmt(t: string | null) {
  return t ? t.replace('T', ' ').slice(0, 16) : '—'
}
function editorName(id: number | null) {
  if (id == null) return '—'
  return userNames.value[id] || `用户#${id}`
}

const inputCls = 'w-full border border-line rounded-lg px-3.5 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20'
const labelCls = 'block text-[13px] text-muted mb-1.5'
</script>

<template>
  <div>
    <div class="bg-white rounded-xl border border-line">
      <div class="flex items-center gap-3 p-4 border-b border-line flex-wrap">
        <input v-model="keyword" :class="inputCls + ' w-56'" placeholder="搜索名称/简称" @keyup.enter="load" />
        <select v-model="goodsType" :class="inputCls + ' w-32'" @change="load">
          <option value="">全部类型</option>
          <option v-for="g in goodsTypes" :key="g" :value="g">{{ g }}</option>
        </select>
        <select v-model="chainFilter" :class="inputCls + ' w-44'" @change="load">
          <option value="">全部链路方</option>
          <option v-for="c in chains" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
        <button class="px-5 py-2.5 rounded-lg text-[13px] border border-line text-muted hover:bg-slate-50 transition" @click="load">搜索</button>
        <button class="ml-auto px-5 py-2.5 rounded-lg text-[13px] bg-primary text-white transition whitespace-nowrap shrink-0" @click="openCreate">+ 新增供货方</button>
      </div>
      <table class="w-full text-sm">
        <thead>
          <tr class="text-left text-muted text-[13px] border-b border-line">
            <th class="px-5 py-3.5 font-medium">名称</th>
            <th class="px-5 py-3.5 font-medium">链路方</th>
            <th class="px-5 py-3.5 font-medium">类型</th>
            <th class="px-5 py-3.5 font-medium">采购方式</th>
            <th class="px-5 py-3.5 font-medium">报价</th>
            <th class="px-5 py-3.5 font-medium">保障</th>
            <th class="px-5 py-3.5 font-medium">优先级</th>
            <th class="px-5 py-3.5 font-medium">合作状态</th>
            <th class="px-5 py-3.5 font-medium">维护人/更新</th>
            <th class="px-5 py-3.5 font-medium text-right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading"><td colspan="10" class="px-4 py-8 text-center text-muted">加载中…</td></tr>
          <tr v-else-if="!rows.length"><td colspan="10" class="px-4 py-8 text-center text-muted">暂无供货方,点击右上角新增</td></tr>
          <tr v-for="s in rows" :key="s.id" class="border-b border-line hover:bg-slate-50/60 transition">
            <td class="px-5 py-3.5">
              <div class="font-medium">{{ s.name }}</div>
              <div v-if="s.short_name" class="text-xs text-muted">{{ s.short_name }}</div>
            </td>
            <td class="px-5 py-3.5 text-muted">{{ chainName(s.chain_id) }}</td>
            <td class="px-5 py-3.5">
              <span class="text-xs px-2 py-0.5 rounded" :class="s.goods_type === '现货' ? 'bg-blue-50 text-blue-600' : s.goods_type === '准现货' ? 'bg-amber-50 text-amber-600' : 'bg-slate-100 text-slate-500'">{{ s.goods_type }}</span>
            </td>
            <td class="px-5 py-3.5 text-muted">{{ (s.procurement_modes || []).join(' / ') || '—' }}</td>
            <td class="px-5 py-3.5" style="font-variant-numeric: tabular-nums">{{ s.price != null ? `${s.price.toLocaleString()} ${s.currency}` : '—' }}</td>
            <td class="px-5 py-3.5 text-muted">{{ s.guarantee_type ? `${s.guarantee_type}${s.guarantee_ratio ? ' ' + s.guarantee_ratio : ''}` : '—' }}</td>
            <td class="px-5 py-3.5">
              <select
                :value="priorities[s.id] ?? ''"
                class="border border-line rounded-lg px-2 py-1 text-xs outline-none focus:border-primary bg-white"
                @change="quickPriority(s, Number(($event.target as HTMLSelectElement).value))"
              >
                <option value="">默认</option>
                <option v-for="n in 9" :key="n" :value="n">{{ n }}</option>
              </select>
            </td>
            <td class="px-5 py-3.5">
              <span class="text-xs px-2 py-0.5 rounded" :class="s.coop_status === '合作中' ? 'bg-green-50 text-green-600' : s.coop_status === '终止' ? 'bg-red-50 text-red-600' : 'bg-slate-100 text-slate-600'">{{ s.coop_status }}</span>
            </td>
            <td class="px-5 py-3.5 text-muted text-[13px]">{{ editorName(s.last_editor_id) }}<br>{{ fmt(s.updated_at) }}</td>
            <td class="px-5 py-3.5 text-right whitespace-nowrap">
              <button class="text-[13px] text-primary hover:underline mr-3" @click="openDetail(s)">详情</button>
              <button class="text-[13px] text-primary hover:underline mr-3" @click="openEdit(s)">编辑</button>
              <button class="text-[13px] text-red-500 hover:underline" @click="remove(s)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 编辑弹窗 -->
    <div v-if="dialog.show" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50" @click.self="dialog.show = false">
      <div class="bg-white rounded-xl w-[760px] max-h-[86vh] overflow-y-auto shadow-2xl">
        <div class="px-6 py-4 border-b border-line sticky top-0 bg-white rounded-t-xl z-10">
          <div class="text-sm font-bold">{{ dialog.mode === 'create' ? '新增供货方' : `编辑:${dialog.target?.name}` }}</div>
        </div>
        <div class="p-6 grid grid-cols-2 gap-4">
          <div class="col-span-2 text-[13px] font-bold text-primary pt-1">基础信息</div>
          <div><label :class="labelCls">供货方名称 *</label><input v-model="form.name" :class="inputCls" /></div>
          <div><label :class="labelCls">简称</label><input v-model="form.short_name" :class="inputCls" /></div>
          <div><label :class="labelCls">注册地</label><input v-model="form.reg_location" :class="inputCls" /></div>
          <div><label :class="labelCls">统一社会信用代码/注册号</label><input v-model="form.credit_code" :class="inputCls" /></div>
          <div><label :class="labelCls">成立时间</label><input v-model="form.established_at" type="date" :class="inputCls" /></div>
          <div><label :class="labelCls">注册资本</label><input v-model="form.registered_capital" :class="inputCls" /></div>
          <div class="col-span-2"><label :class="labelCls">股权结构</label><textarea v-model="form.equity_structure" :class="inputCls" rows="2"></textarea></div>

          <div class="col-span-2 text-[13px] font-bold text-primary pt-2">链路归属(必须标注海外链路方)</div>
          <div>
            <label :class="labelCls">所属海外链路方 *</label>
            <select v-model="form.chain_id" :class="inputCls">
              <option :value="null">未选择</option>
              <option v-for="c in chains" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
          </div>
          <div><label :class="labelCls">链路角色</label><select v-model="form.chain_role" :class="inputCls"><option value="">未设置</option><option v-for="r in chainRoles" :key="r" :value="r">{{ r }}</option></select></div>

          <div class="col-span-2 text-[13px] font-bold text-primary pt-2">交易属性</div>
          <div>
            <label :class="labelCls">采购方式(可多选)</label>
            <div class="flex gap-2">
              <button v-for="m in modeOptions" :key="m" type="button" class="px-3 py-1.5 rounded-lg text-[13px] border transition" :class="((form.procurement_modes as string[]) || []).includes(m) ? 'border-primary bg-blue-50 text-primary' : 'border-line text-muted hover:border-slate-400'" @click="toggleMode(m)">{{ m }}</button>
            </div>
          </div>
          <div><label :class="labelCls">期货/现货/准现货</label><select v-model="form.goods_type" :class="inputCls"><option v-for="g in goodsTypes" :key="g" :value="g">{{ g }}</option></select></div>
          <div><label :class="labelCls">报价(单价/整机价)</label><input v-model="form.price" type="number" :class="inputCls" /></div>
          <div><label :class="labelCls">币种</label><select v-model="form.currency" :class="inputCls"><option value="CNY">CNY 人民币</option><option value="USD">USD 美元</option><option value="HKD">HKD 港币</option></select></div>
          <div><label :class="labelCls">报价有效期</label><input v-model="form.price_valid_until" type="date" :class="inputCls" /></div>
          <div><label :class="labelCls">起订量(MOQ)</label><input v-model="form.moq" :class="inputCls" /></div>
          <div><label :class="labelCls">交货周期</label><input v-model="form.delivery_cycle" :class="inputCls" /></div>
          <div><label :class="labelCls">发票类型</label><input v-model="form.invoice_type" :class="inputCls" /></div>
          <div class="col-span-2"><label :class="labelCls">付款节点(定金比例/尾款节点)</label><input v-model="form.payment_terms" :class="inputCls" /></div>

          <div class="col-span-2 text-[13px] font-bold text-primary pt-2">反向保障</div>
          <div><label :class="labelCls">保障措施</label><select v-model="form.guarantee_type" :class="inputCls"><option value="">未设置</option><option v-for="g in guaranteeTypes" :key="g" :value="g">{{ g }}</option></select></div>
          <div><label :class="labelCls">保函比例</label><input v-model="form.guarantee_ratio" :class="inputCls" placeholder="如 30%" /></div>
          <div><label :class="labelCls">保函开具方</label><select v-model="form.guarantee_issuer" :class="inputCls"><option value="">未设置</option><option v-for="g in guaranteeIssuers" :key="g" :value="g">{{ g }}</option></select></div>
          <div><label :class="labelCls">开具主体名称</label><input v-model="form.guarantee_issuer_name" :class="inputCls" /></div>
          <div><label :class="labelCls">保障有效期</label><input v-model="form.guarantee_valid_until" type="date" :class="inputCls" /></div>
          <div><label :class="labelCls">垫资能力</label><input v-model="form.financing_capacity" :class="inputCls" /></div>
          <div class="col-span-2"><label :class="labelCls">兜底条款备注</label><textarea v-model="form.guarantee_notes" :class="inputCls" rows="2"></textarea></div>

          <div class="col-span-2 text-[13px] font-bold text-primary pt-2">合作评价(内部)</div>
          <div><label :class="labelCls">合作状态</label><select v-model="form.coop_status" :class="inputCls"><option v-for="c in coopStatuses" :key="c" :value="c">{{ c }}</option></select></div>
          <div><label :class="labelCls">内部信用评级</label><input v-model="form.credit_rating" :class="inputCls" placeholder="如 A/B/C" /></div>
          <div><label :class="labelCls">历史成交次数</label><input v-model="form.deal_count" type="number" :class="inputCls" /></div>
          <div><label :class="labelCls">履约率</label><input v-model="form.fulfillment_rate" :class="inputCls" placeholder="如 100%" /></div>
          <div class="col-span-2"><label :class="labelCls">风险备注</label><textarea v-model="form.risk_notes" :class="inputCls" rows="2"></textarea></div>
        </div>
        <div class="px-6 py-4 border-t border-line flex items-center justify-end gap-2 sticky bottom-0 bg-white rounded-b-xl">
          <p v-if="formError" class="text-[13px] text-red-500 mr-auto">{{ formError }}</p>
          <button class="px-5 py-2.5 rounded-lg text-[13px] border border-line text-muted hover:bg-slate-50 transition" @click="dialog.show = false">取消</button>
          <button class="px-5 py-2.5 rounded-lg text-[13px] bg-primary text-white transition" @click="submit">保存</button>
        </div>
      </div>
    </div>

    <!-- 详情抽屉 -->
    <SupplierDetail v-if="detail" :supplier="detail" :chains="chains" :user-names="userNames" @close="onDetailClosed" />
  </div>
</template>
