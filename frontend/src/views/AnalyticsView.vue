<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { fetchAnalytics, type AnalyticsOverview } from '../api/orders'
import { errMsg } from '../api/http'

const data = ref<AnalyticsOverview | null>(null)

// 升级配色:蓝→青→紫→绿→琥珀→玫红,克制高级
const PALETTE = ['#2563EB', '#06B6D4', '#8B5CF6', '#10B981', '#F59E0B', '#F43F5E', '#1E3A8A', '#64748B']
const TEXT = '#94A3B8'
const GRID = '#EEF2F7'

const refs: Record<string, HTMLDivElement | null> = {}
const charts: Record<string, echarts.ECharts> = {}
function setRef(key: string) {
  return (el: unknown) => {
    refs[key] = el as HTMLDivElement | null
  }
}

function render(key: string, option: echarts.EChartsOption) {
  const el = refs[key]
  if (!el) return
  if (!charts[key]) {
    charts[key] = echarts.init(el)
    const ro = new ResizeObserver(() => charts[key]?.resize())
    ro.observe(el)
  }
  charts[key].setOption(option, true)
  requestAnimationFrame(() => charts[key]?.resize())
}

const axisBase = {
  axisLine: { lineStyle: { color: GRID } },
  axisLabel: { color: TEXT, fontSize: 10 },
  splitLine: { lineStyle: { color: GRID } },
}
const legendBase = { textStyle: { color: '#64748B', fontSize: 11 }, itemWidth: 10, itemHeight: 10, top: 0 }

function buildCharts(d: AnalyticsOverview) {
  const months = d.amount_trend.map((m) => m.month.slice(5))

  // 成交金额趋势(渐变面积)
  render('amountTrend', {
    grid: { left: 52, right: 14, top: 30, bottom: 28 },
    tooltip: { trigger: 'axis', valueFormatter: (v) => `${(v as number).toLocaleString()} 万` },
    xAxis: { type: 'category', data: months, ...axisBase },
    yAxis: { type: 'value', ...axisBase, axisLabel: { color: TEXT, fontSize: 10, formatter: (v: number) => (v >= 10000 ? `${v / 10000}亿` : `${v}万`) } },
    series: [
      {
        name: '成交金额',
        type: 'line',
        smooth: true,
        data: d.amount_trend.map((m) => m.amount),
        lineStyle: { width: 2.5, color: '#2563EB' },
        itemStyle: { color: '#2563EB' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(37,99,235,0.26)' },
            { offset: 1, color: 'rgba(37,99,235,0.02)' },
          ]),
        },
      },
    ],
  })

  // 新增主体(柱)
  render('newTrend', {
    grid: { left: 40, right: 14, top: 38, bottom: 28 },
    tooltip: { trigger: 'axis' },
    legend: { ...legendBase, data: ['新增供货方', '新增客户'] },
    xAxis: { type: 'category', data: d.monthly_trend.map((m) => m.month.slice(5)), ...axisBase },
    yAxis: { type: 'value', minInterval: 1, ...axisBase },
    series: [
      { name: '新增供货方', type: 'bar', data: d.monthly_trend.map((m) => m.suppliers), itemStyle: { color: '#2563EB', borderRadius: [3, 3, 0, 0] }, barMaxWidth: 12 },
      { name: '新增客户', type: 'bar', data: d.monthly_trend.map((m) => m.customers), itemStyle: { color: '#06B6D4', borderRadius: [3, 3, 0, 0] }, barMaxWidth: 12 },
    ],
  })

  // 货源结构环形
  render('goodsPie', {
    tooltip: { trigger: 'item' },
    legend: { ...legendBase, bottom: 0, orient: 'horizontal', left: 'center' },
    series: [
      {
        type: 'pie',
        radius: ['40%', '64%'],
        center: ['50%', '47%'],
        itemStyle: { borderColor: '#fff', borderWidth: 2 },
        label: { show: false },
        data: d.goods_structure.filter((g) => g.count > 0).map((g, i) => ({ name: g.type, value: g.count, itemStyle: { color: PALETTE[i % PALETTE.length] } })),
      },
    ],
  })

  // 付款方式环形(金额)
  render('payPie', {
    tooltip: { trigger: 'item', valueFormatter: (v) => `${(v as number).toLocaleString()} 万` },
    legend: { ...legendBase, bottom: 0, orient: 'horizontal', left: 'center' },
    series: [
      {
        type: 'pie',
        radius: ['40%', '64%'],
        center: ['50%', '47%'],
        itemStyle: { borderColor: '#fff', borderWidth: 2 },
        label: { show: false },
        data: d.payment_mode_dist.filter((p) => p.amount > 0).map((p, i) => ({ name: p.mode, value: Math.round(p.amount), itemStyle: { color: PALETTE[i % PALETTE.length] } })),
      },
    ],
  })

  // 配额时效条形
  render('agingBar', {
    grid: { left: 46, right: 14, top: 26, bottom: 30 },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: d.quota_aging.map((a) => a.bucket), ...axisBase },
    yAxis: { type: 'value', minInterval: 1, ...axisBase },
    series: [
      {
        type: 'bar',
        data: d.quota_aging.map((a) => ({ value: a.count, itemStyle: { color: a.bucket === '已过期' ? '#F43F5E' : a.bucket === '7天内' ? '#F59E0B' : a.bucket === '7-30天' ? '#06B6D4' : '#10B981', borderRadius: [3, 3, 0, 0] } })),
        barMaxWidth: 26,
      },
    ],
  })

  // 配额按链路方横向条形
  render('chainBar', {
    grid: { left: 96, right: 44, top: 18, bottom: 18 },
    tooltip: { trigger: 'axis', valueFormatter: (v) => `${(v as number).toLocaleString()} 台` },
    xAxis: { type: 'value', ...axisBase },
    yAxis: { type: 'category', data: d.quota_by_chain.map((c) => c.name).reverse(), ...axisBase, axisLabel: { color: '#64748B', fontSize: 10 } },
    series: [
      {
        type: 'bar',
        data: d.quota_by_chain.map((c, i) => ({ value: c.available, itemStyle: { color: PALETTE[(d.quota_by_chain.length - 1 - i) % PALETTE.length], borderRadius: [0, 3, 3, 0] } })).reverse(),
        barMaxWidth: 14,
      },
    ],
  })

  // 验资状态环形
  render('verifyPie', {
    tooltip: { trigger: 'item' },
    legend: { ...legendBase, bottom: 0, orient: 'horizontal', left: 'center' },
    series: [
      {
        type: 'pie',
        radius: ['40%', '64%'],
        center: ['50%', '47%'],
        itemStyle: { borderColor: '#fff', borderWidth: 2 },
        label: { show: false },
        data: [
          { name: '已验资', value: d.verification_dist.verified, itemStyle: { color: '#10B981' } },
          { name: '待终审', value: d.verification_dist.pending, itemStyle: { color: '#F59E0B' } },
          { name: '未验资', value: d.verification_dist.unverified, itemStyle: { color: '#CBD5E1' } },
        ],
      },
    ],
  })

  // 客户分级柱
  render('gradeBar', {
    grid: { left: 40, right: 14, top: 26, bottom: 30 },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: d.value_grade_dist.map((g) => `${g.grade} 级`), ...axisBase },
    yAxis: { type: 'value', minInterval: 1, ...axisBase },
    series: [
      {
        type: 'bar',
        data: d.value_grade_dist.map((g, i) => ({ value: g.count, itemStyle: { color: ['#1E3A8A', '#2563EB', '#06B6D4'][i % 3], borderRadius: [3, 3, 0, 0] } })),
        barMaxWidth: 26,
      },
    ],
  })

  // 履约率分布
  render('fulfillBar', {
    grid: { left: 46, right: 14, top: 26, bottom: 30 },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: d.fulfillment_dist.map((f) => f.bucket), ...axisBase },
    yAxis: { type: 'value', minInterval: 1, ...axisBase },
    series: [
      {
        type: 'bar',
        data: d.fulfillment_dist.map((f) => ({ value: f.count, itemStyle: { color: f.bucket === '≥95%' ? '#10B981' : f.bucket === '<95%' ? '#F59E0B' : '#CBD5E1', borderRadius: [3, 3, 0, 0] } })),
        barMaxWidth: 26,
      },
    ],
  })
}

const hasAmount = computed(() => (data.value?.amount_trend ?? []).some((m) => m.amount > 0))
const hasGoods = computed(() => (data.value?.goods_structure ?? []).some((g) => g.count > 0))
const hasPay = computed(() => (data.value?.payment_mode_dist ?? []).some((p) => p.amount > 0))
const hasAging = computed(() => (data.value?.quota_aging ?? []).some((a) => a.count > 0))
const hasChains = computed(() => (data.value?.quota_by_chain ?? []).some((c) => c.available > 0))
const hasVerify = computed(() => {
  const v = data.value?.verification_dist
  return !!v && v.verified + v.pending + v.unverified > 0
})
const hasGrades = computed(() => (data.value?.value_grade_dist ?? []).some((g) => g.count > 0))
const hasFulfill = computed(() => (data.value?.fulfillment_dist ?? []).some((f) => f.count > 0))
const hasTrend = computed(() => (data.value?.monthly_trend ?? []).some((m) => m.suppliers > 0 || m.customers > 0))
const emptyCls = 'flex items-center justify-center h-full text-[13px] text-muted'

async function load() {
  try {
    data.value = await fetchAnalytics()
    // 等待 v-if 图表容器挂载后再初始化(否则 refs 为空,图表空白)
    await nextTick()
    buildCharts(data.value)
  } catch (e) {
    alert(errMsg(e))
  }
}
onMounted(() => {
  load()
  window.addEventListener('resize', () => {
    Object.values(charts).forEach((c) => c.resize())
  })
})

const money = (v: number) => {
  const n = Number(v) || 0
  if (n >= 10000) {
    const yi = (n / 10000).toFixed(2).replace(/0+$/, '').replace(/\.$/, '')
    return `${yi} 亿`
  }
  return `${n.toLocaleString(undefined, { maximumFractionDigits: 2 })} 万`
}
function fmt(t: string) {
  return t ? t.replace('T', ' ').slice(0, 16) : '—'
}
const actionMeta: Record<string, string> = { create: '创建', update: '更新', delete: '删除', login: '登录' }
</script>

<template>
  <div v-if="data">
    <!-- KPI 第一行:主体与成交 -->
    <div class="grid grid-cols-4 gap-4 mb-4">
      <div class="bg-white rounded-xl border border-line p-5 border-l-4" style="border-left-color: #2563EB">
        <div class="text-[13px] text-muted">上游供货方</div>
        <div class="text-3xl font-bold mt-2" style="font-variant-numeric: tabular-nums; color: #1E3A8A">{{ data.supplier_count }}</div>
        <div class="text-xs text-muted mt-1.5">海外链路方 {{ data.chain_count }} 条</div>
      </div>
      <div class="bg-white rounded-xl border border-line p-5 border-l-4" style="border-left-color: #06B6D4">
        <div class="text-[13px] text-muted">下游客户</div>
        <div class="text-3xl font-bold mt-2" style="font-variant-numeric: tabular-nums">{{ data.customer_count }}</div>
        <div class="text-xs text-muted mt-1.5">验资完成率 {{ data.verified_rate }}%</div>
      </div>
      <div class="bg-white rounded-xl border border-line p-5 border-l-4" style="border-left-color: #8B5CF6">
        <div class="text-[13px] text-muted">在途订单</div>
        <div class="text-3xl font-bold mt-2" style="font-variant-numeric: tabular-nums">{{ data.active_orders }}</div>
        <div class="text-xs text-muted mt-1.5">中间层 {{ data.middle_count }} 个</div>
      </div>
      <div class="bg-white rounded-xl border border-line p-5 border-l-4" style="border-left-color: #10B981">
        <div class="text-[13px] text-muted">本月成交额</div>
        <div class="text-3xl font-bold mt-2" style="font-variant-numeric: tabular-nums; color: #047857">{{ money(data.month_amount) }}</div>
        <div class="text-xs text-muted mt-1.5">按订单录入时间统计</div>
      </div>
    </div>

    <!-- KPI 第二行:资金与风险 -->
    <div class="grid grid-cols-4 gap-4 mb-5">
      <div class="bg-white rounded-xl border border-line p-5 border-l-4" style="border-left-color: #F59E0B">
        <div class="text-[13px] text-muted">在途资金敞口(未完成订单)</div>
        <div class="text-3xl font-bold mt-2" style="font-variant-numeric: tabular-nums; color: #B45309">{{ money(data.funding_in_progress) }}</div>
        <div class="text-xs text-muted mt-1.5">已录入未交付的订单金额合计</div>
      </div>
      <div class="bg-white rounded-xl border border-line p-5 border-l-4" style="border-left-color: #2563EB">
        <div class="text-[13px] text-muted">中间层截流峰值合计</div>
        <div class="text-3xl font-bold mt-2" style="font-variant-numeric: tabular-nums">{{ money(data.middle_held_total) }}</div>
        <div class="text-xs text-muted mt-1.5">交易方案代管资金峰值汇总</div>
      </div>
      <div class="bg-white rounded-xl border border-line p-5 border-l-4" style="border-left-color: #06B6D4">
        <div class="text-[13px] text-muted">需求覆盖率</div>
        <div class="text-3xl font-bold mt-2" style="font-variant-numeric: tabular-nums">{{ data.demand_coverage.rate != null ? data.demand_coverage.rate + '%' : '—' }}</div>
        <div class="text-xs text-muted mt-1.5">意向 {{ data.demand_coverage.intent_qty }} 台 / 可用配额 {{ data.demand_coverage.available_qty }} 台</div>
      </div>
      <div class="bg-white rounded-xl border border-line p-5 border-l-4" style="border-left-color: #F43F5E">
        <div class="text-[13px] text-muted">违约订单</div>
        <div class="text-3xl font-bold mt-2" style="font-variant-numeric: tabular-nums; color: #DC2626">{{ data.breach_count }}</div>
        <div class="text-xs text-muted mt-1.5">违约/违约处理中</div>
      </div>
    </div>

    <!-- 图表行 1:成交趋势 + 新增趋势 -->
    <div class="grid grid-cols-3 gap-4 mb-4">
      <div class="col-span-2 bg-white rounded-xl border border-line p-5">
        <div class="text-sm font-bold mb-2">近 12 个月成交金额趋势</div>
        <div v-if="hasAmount" :ref="setRef('amountTrend')" class="h-[240px]"></div>
        <div v-else :class="emptyCls" style="height: 240px">暂无成交数据</div>
      </div>
      <div class="bg-white rounded-xl border border-line p-5">
        <div class="text-sm font-bold mb-2">近 12 个月新增主体</div>
        <div v-if="hasTrend" :ref="setRef('newTrend')" class="h-[240px]"></div>
        <div v-else :class="emptyCls" style="height: 240px">暂无新增主体</div>
      </div>
    </div>

    <!-- 图表行 2:货源结构 + 付款方式 + 配额时效 -->
    <div class="grid grid-cols-3 gap-4 mb-4">
      <div class="bg-white rounded-xl border border-line p-5">
        <div class="text-sm font-bold mb-2">货源结构(现货/准现货/期货)</div>
        <div v-if="hasGoods" :ref="setRef('goodsPie')" class="h-[200px]"></div>
        <div v-else :class="emptyCls" style="height: 200px">暂无供货方</div>
      </div>
      <div class="bg-white rounded-xl border border-line p-5">
        <div class="text-sm font-bold mb-2">付款方式分布(按金额)</div>
        <div v-if="hasPay" :ref="setRef('payPie')" class="h-[200px]"></div>
        <div v-else :class="emptyCls" style="height: 200px">暂无订单</div>
      </div>
      <div class="bg-white rounded-xl border border-line p-5">
        <div class="text-sm font-bold mb-2">配额时效分布(批次)</div>
        <div v-if="hasAging" :ref="setRef('agingBar')" class="h-[200px]"></div>
        <div v-else :class="emptyCls" style="height: 200px">暂无配额</div>
      </div>
    </div>

    <!-- 图表行 3:配额按链路 + 验资 + 分级 -->
    <div class="grid grid-cols-3 gap-4 mb-4">
      <div class="bg-white rounded-xl border border-line p-5">
        <div class="text-sm font-bold mb-2">可用配额按海外链路方</div>
        <div v-if="hasChains" :ref="setRef('chainBar')" class="h-[220px]"></div>
        <div v-else :class="emptyCls" style="height: 220px">暂无链路配额</div>
      </div>
      <div class="bg-white rounded-xl border border-line p-5">
        <div class="text-sm font-bold mb-2">客户验资状态</div>
        <div v-if="hasVerify" :ref="setRef('verifyPie')" class="h-[200px]"></div>
        <div v-else :class="emptyCls" style="height: 200px">暂无客户</div>
      </div>
      <div class="bg-white rounded-xl border border-line p-5">
        <div class="text-sm font-bold mb-2">客户价值分级</div>
        <div v-if="hasGrades" :ref="setRef('gradeBar')" class="h-[200px]"></div>
        <div v-else :class="emptyCls" style="height: 200px">暂无分级数据</div>
      </div>
    </div>

    <!-- 图表行 4:履约率 + 到期预警 + 动态 -->
    <div class="grid grid-cols-3 gap-4">
      <div class="bg-white rounded-xl border border-line p-5">
        <div class="text-sm font-bold mb-2">供货方履约率分布</div>
        <div v-if="hasFulfill" :ref="setRef('fulfillBar')" class="h-[180px]"></div>
        <div v-else :class="emptyCls" style="height: 180px">暂无供货方</div>
      </div>
      <div class="bg-white rounded-xl border border-line p-5">
        <div class="text-sm font-bold mb-3">配额到期预警(7 天内)</div>
        <div v-if="!data.expiring_quotas.length" class="text-[13px] text-muted py-8 text-center">暂无即将到期的配额</div>
        <div v-for="q in data.expiring_quotas" :key="q.quota_id" class="border border-line rounded-lg p-3 mb-2">
          <div class="text-[13px] font-medium">{{ q.supplier }} · {{ q.batch_no || '#' + q.quota_id }}</div>
          <div class="text-xs text-muted mt-1">到期 {{ q.end_at }}
            <span class="px-1.5 py-0.5 rounded ml-1" :class="q.remain <= 2 ? 'bg-red-50 text-red-600' : 'bg-amber-50 text-amber-600'">剩 {{ q.remain }} 天</span>
          </div>
        </div>
      </div>
      <div class="bg-white rounded-xl border border-line p-5">
        <div class="text-sm font-bold mb-3">主体动态(最近操作)</div>
        <div class="max-h-[240px] overflow-y-auto">
          <div v-for="(d2, i) in data.dynamics" :key="i" class="border-b border-line last:border-0 py-2">
            <div class="flex items-center gap-2 text-xs">
              <span class="text-muted whitespace-nowrap">{{ fmt(d2.at) }}</span>
              <span class="font-medium">{{ d2.username }}</span>
              <span class="px-1.5 py-0.5 rounded" :class="d2.action === 'create' ? 'bg-green-50 text-green-600' : d2.action === 'delete' ? 'bg-red-50 text-red-600' : 'bg-blue-50 text-blue-600'">{{ actionMeta[d2.action] || d2.action }}</span>
            </div>
            <div class="text-xs text-muted mt-0.5 truncate">{{ d2.detail }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
  <div v-else class="bg-white rounded-xl border border-line py-12 text-center text-muted text-[13px]">加载中…</div>
</template>
