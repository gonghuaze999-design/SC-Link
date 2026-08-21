<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { fetchDashboard, ORDER_STATUSES, type DashboardOverview } from '../api/orders'
import { errMsg } from '../api/http'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const data = ref<DashboardOverview | null>(null)
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    data.value = await fetchDashboard()
  } catch (e) {
    alert(errMsg(e))
  } finally {
    loading.value = false
  }
}
onMounted(load)

function fmt(t: string) {
  return t ? t.replace('T', ' ').slice(0, 16) : '—'
}
const money = (v: number) => `${(v ?? 0).toLocaleString()} 万`

const quickActions = [
  { label: '发布看板', path: '/board' },
  { label: '录入订单', path: '/orders' },
  { label: '开始匹配', path: '/match' },
  { label: '新增主体', path: '/entities' },
]
</script>

<template>
  <div v-if="data" class="space-y-5">
    <!-- 顶部:问候 + 快捷操作 -->
    <div class="bg-white rounded-xl border border-line p-6 flex items-center gap-4 flex-wrap">
      <div>
        <div class="text-xl font-bold">你好,{{ auth.user?.display_name || auth.user?.username }}</div>
        <div class="text-[13px] text-muted mt-1.5">待审批 {{ data.pending_shares + data.pending_detail_requests }} 项 · 在途订单 {{ data.active_orders_count }} 单 · 到期提醒 {{ data.expiring.length }} 条</div>
      </div>
      <div class="ml-auto flex gap-2 flex-wrap">
        <button v-for="a in quickActions" :key="a.path" class="px-4 py-2.5 rounded-lg text-[13px] bg-primary text-white hover:bg-primary/90 transition whitespace-nowrap" @click="router.push(a.path)">
          + {{ a.label }}
        </button>
      </div>
    </div>

    <!-- 值班简报摘要 -->
    <div class="bg-white rounded-xl border border-line p-5">
      <div class="flex items-center gap-2 mb-2">
        <div class="w-2 h-2 rounded-full bg-cyan-400"></div>
        <div class="text-sm font-bold">值班机器人今日简报</div>
        <span v-if="data.unread_duty" class="px-1.5 py-0.5 rounded text-xs bg-red-50 text-red-600">{{ data.unread_duty }} 未读</span>
        <button class="ml-auto text-xs text-primary hover:underline" @click="router.push('/duty')">查看完整简报 →</button>
      </div>
      <div v-if="data.duty?.note" class="text-sm text-emerald-700">{{ data.duty.note }}</div>
      <div v-else-if="data.duty?.ai_text" class="text-[13px] text-muted line-clamp-2">{{ data.duty.ai_text }}</div>
      <div v-else class="text-[13px] text-muted">暂无简报:机器人每日 08:30 自动扫描,也可到「值班机器人」页手动触发</div>
    </div>

    <!-- 待审批 -->
    <div v-if="data.pending_shares || data.pending_detail_requests" class="grid grid-cols-2 gap-4">
      <div v-if="data.pending_shares" class="bg-white rounded-xl border border-amber-200 p-5 flex items-center cursor-pointer hover:shadow-md transition" @click="router.push('/shares')">
        <div class="text-sm font-bold text-amber-600">待审批:数据共享申请 {{ data.pending_shares }} 项</div>
        <div class="ml-auto text-xs text-muted">去处理 →</div>
      </div>
      <div v-if="data.pending_detail_requests" class="bg-white rounded-xl border border-amber-200 p-5 flex items-center cursor-pointer hover:shadow-md transition" @click="router.push('/match')">
        <div class="text-sm font-bold text-amber-600">待审批:详情查看申请 {{ data.pending_detail_requests }} 项</div>
        <div class="ml-auto text-xs text-muted">去处理 →</div>
      </div>
    </div>

    <div class="grid grid-cols-3 gap-4">
      <!-- 左:在途订单 -->
      <div class="col-span-2 bg-white rounded-xl border border-line">
        <div class="px-5 py-3.5 border-b border-line flex items-center">
          <div class="text-sm font-bold">我的在途订单(违约优先)</div>
          <button class="ml-auto text-xs text-primary hover:underline" @click="router.push('/orders')">全部订单 →</button>
        </div>
        <div v-if="!data.orders.length" class="py-10 text-center text-[13px] text-muted">暂无在途订单,点击右上角「+ 录入订单」</div>
        <div v-for="o in data.orders" :key="o.id" class="px-5 py-3 border-b border-line last:border-0 flex items-center gap-3 cursor-pointer hover:bg-slate-50/60" @click="router.push('/orders')">
          <span class="text-xs px-2 py-0.5 rounded shrink-0" :class="ORDER_STATUSES[o.status]?.cls">{{ ORDER_STATUSES[o.status]?.label }}</span>
          <span class="text-[13px] font-medium">{{ o.order_no }}</span>
          <span class="text-xs text-muted">{{ o.quantity }} 台 · {{ money(o.total_amount) }}</span>
          <span class="text-xs text-muted truncate">{{ o.supplier_name }} → {{ o.customer_name }}</span>
          <span class="ml-auto text-xs text-muted whitespace-nowrap">{{ fmt(o.updated_at) }}</span>
        </div>
      </div>

      <!-- 右:到期 + 陈旧 -->
      <div class="space-y-4">
        <div class="bg-white rounded-xl border border-line p-5">
          <div class="text-sm font-bold mb-3">到期提醒(7 天内)</div>
          <div v-if="!data.expiring.length" class="text-[13px] text-muted">暂无到期事项</div>
          <div v-for="e in data.expiring" :key="e.detail" class="text-[13px] py-1.5 border-b border-line last:border-0">
            <span class="px-1.5 py-0.5 rounded text-xs mr-1.5" :class="e.type === '配额' ? 'bg-amber-50 text-amber-600' : 'bg-blue-50 text-blue-600'">{{ e.type }}</span>{{ e.detail }}
          </div>
        </div>
        <div class="bg-white rounded-xl border border-line p-5">
          <div class="text-sm font-bold mb-3">陈旧信息(>3 天未更新)</div>
          <div v-if="!data.stale.length" class="text-[13px] text-muted">信息维护及时,无陈旧数据</div>
          <div v-for="s in data.stale" :key="s.type + s.name" class="text-[13px] py-1.5 border-b border-line last:border-0 flex items-center gap-2">
            <span class="px-1.5 py-0.5 rounded text-xs bg-slate-100 text-slate-600 shrink-0">{{ s.type }}</span>
            <span class="truncate">{{ s.name }}</span>
            <span class="ml-auto text-red-500 text-xs shrink-0">{{ s.days }} 天</span>
          </div>
        </div>
      </div>
    </div>
  </div>
  <div v-else class="bg-white rounded-xl border border-line py-12 text-center text-muted text-[13px]">加载中…</div>
</template>
