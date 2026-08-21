<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import {
  createCommunication,
  listCommunications,
  type Communication,
  type Middle,
} from '../../api/entities'
import { errMsg } from '../../api/http'

const props = defineProps<{ middle: Middle; userNames: Record<number, string> }>()
const emit = defineEmits<{ (e: 'close'): void }>()

const comms = ref<Communication[]>([])
async function load() {
  comms.value = await listCommunications('middle', props.middle.id).catch(() => [])
}
onMounted(load)

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
    await createCommunication('middle', props.middle.id, {
      comm_time: commForm.comm_time ? commForm.comm_time.replace('T', ' ') + ':00' : null,
      channel: commForm.channel,
      participants: commForm.participants,
      content: commForm.content,
      next_step: commForm.next_step,
      follow_up_at: commForm.follow_up_at ? commForm.follow_up_at.replace('T', ' ') + ':00' : null,
    })
    Object.assign(commForm, { comm_time: '', channel: '微信', participants: '', content: '', next_step: '', follow_up_at: '' })
    commDlg.show = false
    load()
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

const groups: { title: string; items: [string, unknown][] }[] = [
  {
    title: '基础信息',
    items: [
      ['主体名称', props.middle.name],
      ['信用代码', props.middle.credit_code || '—'],
      ['企业性质', props.middle.entity_nature || '—'],
      ['所属层级', `第 ${props.middle.layer_no} 层`],
      ['注册地', props.middle.reg_location || '—'],
      ['注册资本', props.middle.registered_capital || '—'],
      ['联系方式', props.middle.contact_info || '—'],
    ],
  },
  {
    title: '账户信息',
    items: [
      ['户名', props.middle.account_info?.户名 || '—'],
      ['开户行', props.middle.account_info?.开户行 || '—'],
      ['账号', props.middle.account_info?.账号 || '—'],
    ],
  },
  {
    title: '开票信息',
    items: [
      ['单位全称', props.middle.invoice_detail?.单位全称 || '—'],
      ['开户行', props.middle.invoice_detail?.开户行 || '—'],
      ['行号/账号', props.middle.invoice_detail?.账号 || '—'],
      ['地址', props.middle.invoice_detail?.地址 || '—'],
      ['联系人', props.middle.invoice_detail?.联系人 || '—'],
      ['联系方式', props.middle.invoice_detail?.联系方式 || '—'],
    ],
  },
  {
    title: '功能定位',
    items: [
      ['目的', (props.middle.purposes || []).join('、') || '—'],
      ['费率/分成', props.middle.fee_rate || '—'],
      ['结算方式', props.middle.settlement || '—'],
      ['合作状态', props.middle.coop_status],
      ['信用评级', props.middle.credit_rating || '—'],
      ['风险备注', props.middle.risk_notes || '—'],
    ],
  },
]
</script>

<template>
  <div class="fixed inset-0 bg-black/40 z-40" @click.self="emit('close')"></div>
  <div class="fixed inset-y-0 right-0 w-[640px] max-w-[92vw] bg-white shadow-2xl z-50 flex flex-col">
    <div class="px-6 py-4 border-b border-line flex items-center shrink-0">
      <div>
        <div class="text-sm font-bold">{{ middle.name }}</div>
        <div class="text-xs text-muted">最后维护:{{ userNames[middle.last_editor_id!] || '—' }} · {{ fmt(middle.updated_at) }} · 版本 v{{ middle.version }}</div>
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

      <div class="flex items-center justify-between mt-6 mb-2">
        <div class="text-[13px] font-bold text-primary">沟通记录(中间层会变化,留痕尤为重要)</div>
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
