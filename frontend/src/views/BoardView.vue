<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  createPublication,
  deletePublication,
  listPublications,
  parsePublication,
  updatePublication,
  type Publication,
} from '../api/match'
import { listProductLines as _pl, listUserOptions } from '../api/entities'
import { errMsg } from '../api/http'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const rows = ref<Publication[]>([])
const products = ref<{ id: number; name: string }[]>([])
const userNames = ref<Record<number, string>>({})
const filterType = ref('')
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    rows.value = await listPublications({ type: filterType.value })
  } catch (e) {
    alert(errMsg(e))
  } finally {
    loading.value = false
  }
}
onMounted(async () => {
  load()
  products.value = await _pl().catch(() => [])
  userNames.value = Object.fromEntries((await listUserOptions().catch(() => [])).map((u) => [u.id, u.display_name || u.username]))
})

const mine = computed(() => rows.value.filter((p) => p.user_id === auth.user?.id))

// ---------- 发布 ----------
const dlg = reactive({ show: false })
const form = reactive({
  type: 'demand',
  product_line_id: null as number | null,
  title: '',
  quantity: '',
  price_min: null as number | null,
  price_max: null as number | null,
  currency: 'CNY',
  validity_days: 7,
  visibility: 'public',
  content: '',
  intent_modes: [] as string[],
  goods_preference: '',
})
const formErr = ref('')
const submitting = ref(false)

const modeOptions = ['预付款', '信用证-国内', '信用证-跨境']
function toggleMode(m: string) {
  form.intent_modes = form.intent_modes.includes(m) ? form.intent_modes.filter((x) => x !== m) : [...form.intent_modes, m]
}

function openCreate() {
  Object.assign(form, {
    type: 'demand', product_line_id: null, title: '', quantity: '', price_min: null, price_max: null,
    currency: 'CNY', validity_days: 7, visibility: 'public', content: '', intent_modes: [], goods_preference: '',
  })
  formErr.value = ''
  dlg.show = true
}

async function submit() {
  formErr.value = ''
  if (!form.title.trim()) {
    formErr.value = '请填写标题'
    return
  }
  submitting.value = true
  try {
    const until = new Date()
    until.setDate(until.getDate() + form.validity_days)
    await createPublication({
      type: form.type,
      product_line_id: form.product_line_id,
      title: form.title,
      quantity: form.quantity,
      price_min: form.price_min,
      price_max: form.price_max,
      currency: form.currency,
      validity_until: until.toISOString().slice(0, 10),
      visibility: form.visibility,
      content: form.content,
      intent_modes: form.intent_modes,
      goods_preference: form.goods_preference,
    })
    dlg.show = false
    load()
  } catch (e) {
    formErr.value = errMsg(e)
  } finally {
    submitting.value = false
  }
}

// ---------- AI 解析 ----------
const aiText = ref('')
const aiLoading = ref(false)
const aiMsg = ref('')
async function aiParse() {
  aiMsg.value = ''
  if (!aiText.value.trim()) {
    aiMsg.value = '请先输入自然语言描述'
    return
  }
  aiLoading.value = true
  try {
    const r = await parsePublication(aiText.value)
    if (r.title) form.title = r.title
    if (r.quantity) form.quantity = String(r.quantity)
    if (r.price_min != null) form.price_min = r.price_min
    if (r.price_max != null) form.price_max = r.price_max
    if (r.intent_modes) form.intent_modes = r.intent_modes
    if (r.goods_preference) form.goods_preference = r.goods_preference
    if (r.content) form.content = r.content
    if (r.product_name) {
      const hit = products.value.find((p) => p.name === r.product_name)
      if (hit) form.product_line_id = hit.id
    }
    aiMsg.value = 'AI 解析完成,请核对后发布'
  } catch (e) {
    aiMsg.value = errMsg(e)
  } finally {
    aiLoading.value = false
  }
}

// ---------- 操作 ----------
async function closePub(p: Publication) {
  try {
    await updatePublication(p.id, { status: 'closed' })
    load()
  } catch (e) {
    alert(errMsg(e))
  }
}
async function removePub(p: Publication) {
  if (!window.confirm(`确认删除发布「${p.title}」?`)) return
  try {
    await deletePublication(p.id)
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
function pname(id: number | null) {
  return id == null ? '未指定' : products.value.find((p) => p.id === id)?.name || `#${id}`
}
</script>

<template>
  <div>
    <div class="flex items-center gap-3 mb-6">
      <div class="flex gap-1 bg-white rounded-xl border border-line p-1.5">
        <button class="px-5 py-2 rounded-lg text-sm transition" :class="filterType === '' ? 'bg-primary text-white shadow' : 'text-muted'" @click="filterType = ''; load()">全部</button>
        <button class="px-5 py-2 rounded-lg text-sm transition" :class="filterType === 'demand' ? 'bg-primary text-white shadow' : 'text-muted'" @click="filterType = 'demand'; load()">采购需求</button>
        <button class="px-5 py-2 rounded-lg text-sm transition" :class="filterType === 'supply' ? 'bg-primary text-white shadow' : 'text-muted'" @click="filterType = 'supply'; load()">供货信息</button>
      </div>
      <div class="text-[13px] text-muted">默认全员可见,可设为私密;到期自动关闭;发布后进入匹配中心</div>
      <button class="ml-auto px-5 py-2.5 rounded-lg text-[13px] bg-primary text-white transition whitespace-nowrap shrink-0" @click="openCreate">+ 发布</button>
    </div>

    <div v-if="loading" class="bg-white rounded-xl border border-line py-10 text-center text-muted text-[13px]">加载中…</div>
    <div v-else-if="!rows.length" class="bg-white rounded-xl border border-line py-10 text-center text-muted text-[13px]">暂无发布,点击右上角发布第一条供需信息</div>

    <div v-else class="grid grid-cols-2 gap-4">
      <div v-for="p in rows" :key="p.id" class="bg-white rounded-xl border border-line p-5 hover:shadow-md transition">
        <div class="flex items-center gap-2 mb-2">
          <span class="text-[13px] px-2.5 py-0.5 rounded font-medium" :class="p.type === 'demand' ? 'bg-blue-50 text-blue-600' : 'bg-green-50 text-green-600'">{{ p.type === 'demand' ? '采购需求' : '供货信息' }}</span>
          <span class="text-[13px] px-2.5 py-0.5 rounded" :class="p.visibility === 'public' ? 'bg-slate-100 text-slate-600' : 'bg-amber-50 text-amber-600'">{{ p.visibility === 'public' ? '公开' : '仅自己可见' }}</span>
          <span v-if="p.status === 'closed'" class="text-[13px] px-2.5 py-0.5 rounded bg-slate-100 text-slate-500">已关闭</span>
        </div>
        <div class="text-[15px] font-semibold mb-1.5">{{ p.title }}</div>
        <div class="text-[13px] text-muted mb-3">
          <div v-if="p.quantity">数量:{{ p.quantity }} · {{ pname(p.product_line_id) }}</div>
          <div v-if="p.price_min != null || p.price_max != null">
            价格:{{ p.price_min != null ? p.price_min.toLocaleString() : '—' }} ~ {{ p.price_max != null ? p.price_max.toLocaleString() : '—' }} {{ p.currency }}
          </div>
          <div v-if="(p.intent_modes || []).length">交易方式:{{ p.intent_modes!.join(' / ') }}</div>
          <div v-if="p.content" class="mt-1 line-clamp-2">{{ p.content }}</div>
        </div>
        <div class="flex items-center text-xs text-muted border-t border-line pt-3">
          <span>{{ userNames[p.user_id] || `用户#${p.user_id}` }} · {{ fmt(p.created_at) }} · 有效期至 {{ p.validity_until || '—' }}</span>
          <span class="ml-auto flex gap-3" v-if="p.user_id === auth.user?.id">
            <button v-if="p.status === 'active'" class="text-[13px] text-muted hover:text-navy" @click="closePub(p)">关闭</button>
            <button class="text-[13px] text-red-500 hover:underline" @click="removePub(p)">删除</button>
          </span>
        </div>
      </div>
    </div>

    <!-- 发布弹窗 -->
    <div v-if="dlg.show" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50" @click.self="dlg.show = false">
      <div class="bg-white rounded-xl w-[640px] max-h-[88vh] overflow-y-auto shadow-2xl">
        <div class="px-6 py-4 border-b border-line sticky top-0 bg-white rounded-t-xl">
          <div class="text-base font-bold">发布供需信息</div>
        </div>
        <div class="p-6 grid grid-cols-2 gap-4">
          <div>
            <label :class="labelCls">发布类型 *</label>
            <div class="flex gap-2">
              <button type="button" class="px-4 py-2 rounded-lg text-[13px] border transition" :class="form.type === 'demand' ? 'border-primary bg-blue-50 text-primary' : 'border-line text-muted'" @click="form.type = 'demand'">采购需求</button>
              <button type="button" class="px-4 py-2 rounded-lg text-[13px] border transition" :class="form.type === 'supply' ? 'border-primary bg-blue-50 text-primary' : 'border-line text-muted'" @click="form.type = 'supply'">供货信息</button>
            </div>
          </div>
          <div>
            <label :class="labelCls">可见范围</label>
            <div class="flex gap-2">
              <button type="button" class="px-4 py-2 rounded-lg text-[13px] border transition" :class="form.visibility === 'public' ? 'border-primary bg-blue-50 text-primary' : 'border-line text-muted'" @click="form.visibility = 'public'">全员可见</button>
              <button type="button" class="px-4 py-2 rounded-lg text-[13px] border transition" :class="form.visibility === 'private' ? 'border-primary bg-blue-50 text-primary' : 'border-line text-muted'" @click="form.visibility = 'private'">仅自己可见</button>
            </div>
          </div>

          <div class="col-span-2">
            <label :class="labelCls">AI 快速发布(可选,自然语言描述后自动填表)</label>
            <div class="flex gap-2">
              <textarea v-model="aiText" :class="inputCls" rows="2" placeholder="如:求购 B300 现货 20 台,资金已备好可预付,预算 1350-1450 万,最好 9 月中旬前交货"></textarea>
              <button type="button" :disabled="aiLoading" class="px-4 py-2 rounded-lg text-[13px] border border-primary text-primary whitespace-nowrap disabled:opacity-60 shrink-0" @click="aiParse">{{ aiLoading ? '解析中…' : 'AI 解析' }}</button>
            </div>
            <p v-if="aiMsg" class="text-xs mt-1" :class="aiMsg.includes('完成') ? 'text-green-600' : 'text-amber-600'">{{ aiMsg }}</p>
          </div>

          <div><label :class="labelCls">标题 *</label><input v-model="form.title" :class="inputCls" placeholder="如:求购 B300 整机 20 台" /></div>
          <div>
            <label :class="labelCls">产品型号</label>
            <select v-model="form.product_line_id" :class="inputCls">
              <option :value="null">未指定</option>
              <option v-for="p in products" :key="p.id" :value="p.id">{{ p.name }}</option>
            </select>
          </div>
          <div><label :class="labelCls">数量</label><input v-model="form.quantity" :class="inputCls" placeholder="如 20 台" /></div>
          <div><label :class="labelCls">现货/期货偏好</label><select v-model="form.goods_preference" :class="inputCls"><option value="">未设置</option><option value="现货">现货</option><option value="准现货">准现货</option><option value="期货">期货</option></select></div>
          <div><label :class="labelCls">最低价(元)</label><input v-model="form.price_min" type="number" :class="inputCls" /></div>
          <div><label :class="labelCls">最高价(元)</label><input v-model="form.price_max" type="number" :class="inputCls" /></div>
          <div><label :class="labelCls">币种</label><select v-model="form.currency" :class="inputCls"><option value="CNY">CNY 人民币</option><option value="USD">USD 美元</option><option value="HKD">HKD 港币</option></select></div>
          <div><label :class="labelCls">有效期(天)</label><select v-model="form.validity_days" :class="inputCls"><option :value="3">3 天</option><option :value="7">7 天</option><option :value="14">14 天</option><option :value="30">30 天</option></select></div>
          <div class="col-span-2">
            <label :class="labelCls">交易方式(可多选)</label>
            <div class="flex gap-2">
              <button v-for="m in modeOptions" :key="m" type="button" class="px-3 py-1.5 rounded-lg text-[13px] border transition" :class="form.intent_modes.includes(m) ? 'border-primary bg-blue-50 text-primary' : 'border-line text-muted hover:border-slate-400'" @click="toggleMode(m)">{{ m }}</button>
            </div>
          </div>
          <div class="col-span-2"><label :class="labelCls">详细描述</label><textarea v-model="form.content" :class="inputCls" rows="3"></textarea></div>
        </div>
        <div class="px-6 py-4 border-t border-line flex items-center justify-end gap-2 sticky bottom-0 bg-white rounded-b-xl">
          <p v-if="formErr" class="text-[13px] text-red-500 mr-auto">{{ formErr }}</p>
          <button class="px-5 py-2.5 rounded-lg text-[13px] border border-line text-muted" @click="dlg.show = false">取消</button>
          <button :disabled="submitting" class="px-5 py-2.5 rounded-lg text-[13px] bg-primary disabled:opacity-60 text-white" @click="submit">{{ submitting ? '发布中…' : '发布(自动进入匹配)' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>
