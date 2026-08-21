<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import {
  createMiddle,
  deleteMiddle,
  listMiddles,
  listUserOptions,
  updateMiddle,
  type Middle,
} from '../../api/entities'
import { errMsg } from '../../api/http'
import MiddleDetail from './MiddleDetail.vue'

const rows = ref<Middle[]>([])
const userNames = ref<Record<number, string>>({})
const keyword = ref('')
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    rows.value = await listMiddles({ keyword: keyword.value })
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

const dialog = reactive({ show: false, mode: 'create' as 'create' | 'edit', target: null as Middle | null })
const form = reactive<Record<string, any>>({})
const formError = ref('')

const purposeOptions = ['代开信用证', '开保函', '居间分账', '意向金截流', '其他']

function blank(): Record<string, any> {
  return {
    name: '', credit_code: '', entity_nature: '', layer_no: 1, reg_location: '',
    registered_capital: '', contact_info: '', purposes: [], fee_rate: '',
    settlement: '', coop_status: '意向', credit_rating: '', risk_notes: '', remark: '',
    account_info: { 户名: '', 开户行: '', 账号: '' },
    invoice_detail: { 单位全称: '', 开户行: '', 账号: '', 地址: '', 联系人: '', 联系方式: '' },
  }
}
function openCreate() {
  dialog.mode = 'create'
  dialog.target = null
  Object.assign(form, blank())
  formError.value = ''
  dialog.show = true
}
function openEdit(m: Middle) {
  dialog.mode = 'edit'
  dialog.target = m
  const b = blank()
  for (const k of Object.keys(b)) form[k] = (m as unknown as Record<string, unknown>)[k] ?? b[k]
  formError.value = ''
  dialog.show = true
}
function togglePurpose(p: string) {
  const arr = (form.purposes as string[]) || []
  form.purposes = arr.includes(p) ? arr.filter((x) => x !== p) : [...arr, p]
}

async function submit() {
  formError.value = ''
  try {
    if (dialog.mode === 'create') await createMiddle(form as Partial<Middle>)
    else if (dialog.target) await updateMiddle(dialog.target.id, { ...form, version: dialog.target.version } as Partial<Middle> & { version: number })
    dialog.show = false
    load()
  } catch (e) {
    formError.value = errMsg(e)
  }
}
async function remove(m: Middle) {
  if (!window.confirm(`确认删除中间层「${m.name}」?操作写入审计日志。`)) return
  try {
    await deleteMiddle(m.id)
    load()
  } catch (e) {
    alert(errMsg(e))
  }
}

const detail = ref<Middle | null>(null)
const inputCls = 'w-full border border-line rounded-lg px-3.5 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20'
const labelCls = 'block text-[13px] text-muted mb-1.5'
function fmt(t: string | null) {
  return t ? t.replace('T', ' ').slice(0, 16) : '—'
}
</script>

<template>
  <div>
    <div class="bg-white rounded-xl border border-line">
      <div class="flex items-center gap-3 p-4 border-b border-line">
        <input v-model="keyword" :class="inputCls + ' w-56'" placeholder="搜索主体名称" @keyup.enter="load" />
        <button class="px-6 py-2.5 rounded-lg text-[13px] border border-line text-muted hover:bg-slate-50 transition whitespace-nowrap shrink-0" @click="load">搜索</button>
        <button class="ml-auto px-5 py-2.5 rounded-lg text-[13px] bg-primary text-white transition whitespace-nowrap shrink-0" @click="openCreate">+ 新增中间层</button>
      </div>
      <table class="w-full text-sm">
        <thead>
          <tr class="text-left text-muted text-[13px] border-b border-line">
            <th class="px-5 py-3.5 font-medium">主体名称</th>
            <th class="px-5 py-3.5 font-medium">企业性质</th>
            <th class="px-5 py-3.5 font-medium">层级</th>
            <th class="px-5 py-3.5 font-medium">目的(可多选)</th>
            <th class="px-5 py-3.5 font-medium">费率</th>
            <th class="px-5 py-3.5 font-medium">合作状态</th>
            <th class="px-5 py-3.5 font-medium">更新</th>
            <th class="px-5 py-3.5 font-medium text-right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading"><td colspan="8" class="px-4 py-8 text-center text-muted">加载中…</td></tr>
          <tr v-else-if="!rows.length"><td colspan="8" class="px-4 py-8 text-center text-muted">暂无中间层,点击右上角新增</td></tr>
          <tr v-for="m in rows" :key="m.id" class="border-b border-line hover:bg-slate-50/60 transition">
            <td class="px-5 py-3.5">
              <div class="font-medium">{{ m.name }}</div>
              <div v-if="m.credit_code" class="text-xs text-muted">{{ m.credit_code }}</div>
            </td>
            <td class="px-5 py-3.5">
              <span v-if="m.entity_nature" class="text-xs px-2 py-0.5 rounded" :class="m.entity_nature === '国资' ? 'bg-amber-50 text-amber-600' : 'bg-slate-100 text-slate-600'">{{ m.entity_nature }}</span>
              <span v-else class="text-muted">—</span>
            </td>
            <td class="px-5 py-3.5 text-muted">第 {{ m.layer_no }} 层</td>
            <td class="px-5 py-3.5 text-muted text-[13px]">{{ (m.purposes || []).join('、') || '—' }}</td>
            <td class="px-5 py-3.5 text-muted">{{ m.fee_rate || '—' }}</td>
            <td class="px-5 py-3.5">
              <span class="text-xs px-2 py-0.5 rounded" :class="m.coop_status === '合作中' ? 'bg-green-50 text-green-600' : 'bg-slate-100 text-slate-600'">{{ m.coop_status }}</span>
            </td>
            <td class="px-5 py-3.5 text-muted text-[13px]">{{ fmt(m.updated_at) }}</td>
            <td class="px-5 py-3.5 text-right whitespace-nowrap">
              <button class="text-[13px] text-primary hover:underline mr-3" @click="detail = m">详情</button>
              <button class="text-[13px] text-primary hover:underline mr-3" @click="openEdit(m)">编辑</button>
              <button class="text-[13px] text-red-500 hover:underline" @click="remove(m)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="dialog.show" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50" @click.self="dialog.show = false">
      <div class="bg-white rounded-xl w-[560px] max-h-[86vh] overflow-y-auto shadow-2xl">
        <div class="px-6 py-4 border-b border-line sticky top-0 bg-white rounded-t-xl">
          <div class="text-sm font-bold">{{ dialog.mode === 'create' ? '新增中间层' : `编辑:${dialog.target?.name}` }}</div>
        </div>
        <div class="p-6 grid grid-cols-2 gap-4">
          <div><label :class="labelCls">主体名称 *</label><input v-model="form.name" :class="inputCls" /></div>
          <div><label :class="labelCls">统一社会信用代码</label><input v-model="form.credit_code" :class="inputCls" /></div>
          <div><label :class="labelCls">企业性质</label><select v-model="form.entity_nature" :class="inputCls"><option value="">未设置</option><option v-for="n in ['国资', '民营', '混合', '其他']" :key="n" :value="n">{{ n }}</option></select></div>
          <div><label :class="labelCls">所属层级</label><select v-model="form.layer_no" :class="inputCls"><option :value="1">第 1 层</option><option :value="2">第 2 层</option></select></div>
          <div><label :class="labelCls">注册地</label><input v-model="form.reg_location" :class="inputCls" /></div>
          <div><label :class="labelCls">注册资本</label><input v-model="form.registered_capital" :class="inputCls" /></div>
          <div class="col-span-2"><label :class="labelCls">联系人/联系方式</label><input v-model="form.contact_info" :class="inputCls" /></div>
          <div class="col-span-2">
            <label :class="labelCls">中间层目的(可多选,因交易模式不同会动态出现)</label>
            <div class="flex gap-2 flex-wrap">
              <button v-for="p in purposeOptions" :key="p" type="button" class="px-3 py-1.5 rounded-lg text-[13px] border transition" :class="((form.purposes as string[]) || []).includes(p) ? 'border-primary bg-blue-50 text-primary' : 'border-line text-muted hover:border-slate-400'" @click="togglePurpose(p)">{{ p }}</button>
            </div>
          </div>
          <div><label :class="labelCls">费率/分成比例</label><input v-model="form.fee_rate" :class="inputCls" /></div>
          <div><label :class="labelCls">结算方式</label><input v-model="form.settlement" :class="inputCls" /></div>
          <div class="col-span-2 text-xs font-bold text-primary pt-1">账户信息</div>
          <div><label :class="labelCls">户名</label><input v-model="form.account_info.户名" :class="inputCls" /></div>
          <div><label :class="labelCls">开户行</label><input v-model="form.account_info.开户行" :class="inputCls" /></div>
          <div class="col-span-2"><label :class="labelCls">账号</label><input v-model="form.account_info.账号" :class="inputCls" /></div>
          <div class="col-span-2 text-xs font-bold text-primary pt-1">开票信息</div>
          <div><label :class="labelCls">单位全称</label><input v-model="form.invoice_detail.单位全称" :class="inputCls" /></div>
          <div><label :class="labelCls">开户行全称</label><input v-model="form.invoice_detail.开户行" :class="inputCls" /></div>
          <div><label :class="labelCls">行号/账号</label><input v-model="form.invoice_detail.账号" :class="inputCls" /></div>
          <div><label :class="labelCls">地址</label><input v-model="form.invoice_detail.地址" :class="inputCls" /></div>
          <div><label :class="labelCls">联系人</label><input v-model="form.invoice_detail.联系人" :class="inputCls" /></div>
          <div><label :class="labelCls">联系方式</label><input v-model="form.invoice_detail.联系方式" :class="inputCls" /></div>
          <div><label :class="labelCls">合作状态</label><select v-model="form.coop_status" :class="inputCls"><option v-for="c in ['意向', '洽谈中', '合作中', '暂停', '终止']" :key="c" :value="c">{{ c }}</option></select></div>
          <div><label :class="labelCls">信用评级</label><input v-model="form.credit_rating" :class="inputCls" /></div>
          <div class="col-span-2"><label :class="labelCls">风险备注</label><textarea v-model="form.risk_notes" :class="inputCls" rows="2"></textarea></div>
          <div class="col-span-2"><label :class="labelCls">备注</label><textarea v-model="form.remark" :class="inputCls" rows="2"></textarea></div>
        </div>
        <div class="px-6 py-4 border-t border-line flex items-center justify-end gap-2 sticky bottom-0 bg-white rounded-b-xl">
          <p v-if="formError" class="text-[13px] text-red-500 mr-auto">{{ formError }}</p>
          <button class="px-5 py-2.5 rounded-lg text-[13px] border border-line text-muted" @click="dialog.show = false">取消</button>
          <button class="px-5 py-2.5 rounded-lg text-[13px] bg-primary text-white" @click="submit">保存</button>
        </div>
      </div>
    </div>

    <MiddleDetail v-if="detail" :middle="detail" :user-names="userNames" @close="detail = null; load()" />
  </div>
</template>
