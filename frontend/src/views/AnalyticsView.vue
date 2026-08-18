<script setup lang="ts">
import { onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { fetchAnalytics, type AnalyticsOverview } from '../api/orders'
import { errMsg } from '../api/http'

const data = ref<AnalyticsOverview | null>(null)
const trendEl = ref<HTMLDivElement | null>(null)

async function load() {
  try {
    data.value = await fetchAnalytics()
    renderTrend()
  } catch (e) {
    alert(errMsg(e))
  }
}
onMounted(load)

function renderTrend() {
  if (!trendEl.value || !data.value) return
  const chart = echarts.init(trendEl.value)
  const months = data.value.monthly_trend.map((m) => m.month.slice(5))
  chart.setOption({
    grid: { left: 40, right: 16, top: 30, bottom: 28 },
    tooltip: { trigger: 'axis' },
    legend: { data: ['新增供货方', '新增客户'], textStyle: { color: '#64748b', fontSize: 11 } },
    xAxis: { type: 'category', data: months, axisLine: { lineStyle: { color: '#e2e8f0' } }, axisLabel: { color: '#94a3b8', fontSize: 10 } },
    yAxis: { type: 'value', minInterval: 1, splitLine: { lineStyle: { color: '#f1f5f9' } }, axisLabel: { color: '#94a3b8', fontSize: 10 } },
    series: [
      { name: '新增供货方', type: 'bar', data: data.value.monthly_trend.map((m) => m.suppliers), itemStyle: { color: '#2563eb', borderRadius: [3, 3, 0, 0] }, barMaxWidth: 16 },
      { name: '新增客户', type: 'bar', data: data.value.monthly_trend.map((m) => m.customers), itemStyle: { color: '#06b6d4', borderRadius: [3, 3, 0, 0] }, barMaxWidth: 16 },
    ],
  })
  window.addEventListener('resize', () => chart.resize())
}

const actionMeta: Record<string, string> = {
  create: '创建', update: '更新', delete: '删除', login: '登录',
}
function fmt(t: string) {
  return t ? t.replace('T', ' ').slice(0, 16) : '—'
}
function money(v: number) {
  if (v >= 100000000) return (v / 100000000).toFixed(2) + ' 亿'
  if (v >= 10000) return (v / 10000).toFixed(0) + ' 万'
  return String(v)
}
</script>

<template>
  <div v-if="data">
    <!-- KPI -->
    <div class="grid grid-cols-4 gap-5 mb-6">
      <div class="bg-white rounded-xl border border-line p-6">
        <div class="text-[13px] text-muted">上游供货方</div>
        <div class="text-3xl font-bold mt-3" style="font-variant-numeric: tabular-nums">{{ data.supplier_count }}</div>
        <div class="text-xs text-muted mt-1.5">海外链路方 {{ data.chain_count }} 条</div>
      </div>
      <div class="bg-white rounded-xl border border-line p-6">
        <div class="text-[13px] text-muted">下游客户</div>
        <div class="text-3xl font-bold mt-3" style="font-variant-numeric: tabular-nums">{{ data.customer_count }}</div>
        <div class="text-xs text-muted mt-1.5">验资完成率 {{ data.verified_rate }}%</div>
      </div>
      <div class="bg-white rounded-xl border border-line p-6">
        <div class="text-[13px] text-muted">在途订单</div>
        <div class="text-3xl font-bold mt-3" style="font-variant-numeric: tabular-nums">{{ data.active_orders }}</div>
        <div class="text-xs text-muted mt-1.5">中间层 {{ data.middle_count }} 个</div>
      </div>
      <div class="bg-white rounded-xl border border-line p-6">
        <div class="text-[13px] text-muted">本月成交额</div>
        <div class="text-3xl font-bold mt-3" style="font-variant-numeric: tabular-nums">{{ money(data.month_amount) }}</div>
        <div class="text-xs text-muted mt-1.5">按订单录入时间统计</div>
      </div>
    </div>

    <div class="grid grid-cols-3 gap-5">
      <!-- 趋势 -->
      <div class="col-span-2 bg-white rounded-xl border border-line p-5">
        <div class="text-sm font-bold mb-2">近 12 个月新增主体趋势</div>
        <div ref="trendEl" class="h-[260px]"></div>
      </div>
      <!-- 配额到期预警 -->
      <div class="bg-white rounded-xl border border-line p-5">
        <div class="text-sm font-bold mb-3">配额到期预警(7 天内)</div>
        <div v-if="!data.expiring_quotas.length" class="text-[13px] text-muted py-6 text-center">暂无即将到期的配额</div>
        <div v-for="q in data.expiring_quotas" :key="q.quota_id" class="border border-line rounded-lg p-3 mb-2">
          <div class="text-[13px] font-medium">{{ q.supplier }} · {{ q.batch_no || `#${q.quota_id}` }}</div>
          <div class="text-xs text-muted mt-1">到期 {{ q.end_at }}
            <span class="px-1.5 py-0.5 rounded ml-1" :class="q.remain <= 2 ? 'bg-red-50 text-red-600' : 'bg-amber-50 text-amber-600'">剩 {{ q.remain }} 天</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 主体动态 -->
    <div class="bg-white rounded-xl border border-line mt-5">
      <div class="px-5 py-3.5 border-b border-line text-sm font-bold">主体动态(最近操作)</div>
      <table class="w-full text-[13px]">
        <tbody>
          <tr v-for="(d, i) in data.dynamics" :key="i" class="border-b border-line last:border-0 hover:bg-slate-50/60">
            <td class="px-5 py-2.5 text-muted whitespace-nowrap">{{ fmt(d.at) }}</td>
            <td class="px-5 py-2.5 font-medium">{{ d.username }}</td>
            <td class="px-5 py-2.5"><span class="text-xs px-2 py-0.5 rounded" :class="d.action === 'create' ? 'bg-green-50 text-green-600' : d.action === 'delete' ? 'bg-red-50 text-red-600' : 'bg-blue-50 text-blue-600'">{{ actionMeta[d.action] || d.action }}</span></td>
            <td class="px-5 py-2.5 text-muted">{{ d.entity_type }}#{{ d.entity_id }}</td>
            <td class="px-5 py-2.5">{{ d.detail }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
  <div v-else class="bg-white rounded-xl border border-line py-12 text-center text-muted text-[13px]">加载中…</div>
</template>
