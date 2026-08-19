<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { latestDuty, listDuty, markDutyRead, runDuty, type DutyReport } from '../api/deal'
import { errMsg } from '../api/http'

const report = ref<DutyReport | null>(null)
const unread = ref(0)
const history = ref<DutyReport[]>([])
const running = ref(false)
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const latest = await latestDuty()
    report.value = latest.report
    unread.value = latest.unread
    history.value = await listDuty(20).catch(() => [])
    if (report.value && !report.value.is_read) markDutyRead(report.value.id)
  } catch (e) {
    alert(errMsg(e))
  } finally {
    loading.value = false
  }
}
onMounted(load)

async function trigger() {
  running.value = true
  try {
    const r = await runDuty()
    report.value = r.report
    history.value = await listDuty(20).catch(() => [])
    markDutyRead(r.report.id)
  } catch (e) {
    alert(errMsg(e))
  } finally {
    running.value = false
  }
}

function fmt(t: string) {
  return t ? t.replace('T', ' ').slice(0, 16) : '—'
}
</script>

<template>
  <div class="space-y-5">
    <div class="bg-white rounded-xl border border-line p-5 flex items-center gap-4">
      <div>
        <div class="text-base font-bold">值班机器人</div>
        <div class="text-[13px] text-muted mt-1">
          每小时自动扫描你权限范围内(含共享授权范围)的供需信息,深度解读并给出撮合建议;<b class="text-amber-600">超过 3 天未更新的需求与供货方信息将额外提醒</b>。
        </div>
      </div>
      <button :disabled="running" class="ml-auto px-5 py-2.5 rounded-lg text-[13px] bg-primary disabled:opacity-60 text-white whitespace-nowrap" @click="trigger">
        {{ running ? '扫描中(约10-30秒)…' : '立即扫描一次' }}
      </button>
    </div>

    <div v-if="loading" class="bg-white rounded-xl border border-line py-12 text-center text-muted text-[13px]">加载中…</div>

    <template v-else-if="report">
      <!-- AI 简报 -->
      <div v-if="report.ai_text" class="bg-white rounded-xl border border-line p-5">
        <div class="flex items-center gap-2 mb-2">
          <div class="w-2 h-2 rounded-full bg-cyan-400"></div>
          <div class="text-sm font-bold">AI 值班简报</div>
          <span class="text-xs text-muted">{{ fmt(report.created_at) }}</span>
        </div>
        <div class="text-sm whitespace-pre-wrap leading-7">{{ report.ai_text }}</div>
      </div>

      <div class="grid grid-cols-3 gap-5">
        <!-- 撮合建议 -->
        <div class="bg-white rounded-xl border border-line p-5 col-span-2">
          <div class="text-sm font-bold mb-3">撮合建议(按匹配度排序)</div>
          <div v-if="!report.content.matches.length" class="text-[13px] text-muted py-4">暂无需求可撮合:发布采购需求或维护客户意向后,机器人会自动分析</div>
          <div v-for="m in report.content.matches" :key="m.demand" class="border border-line rounded-lg p-3 mb-2">
            <div class="text-[13px] font-medium mb-2">{{ m.demand }}</div>
            <div class="space-y-1">
              <div v-for="t in m.top" :key="t.name" class="flex items-center gap-2 text-xs">
                <span class="px-1.5 py-0.5 rounded font-bold" :class="t.score >= 85 ? 'bg-green-50 text-green-600' : t.score >= 70 ? 'bg-blue-50 text-blue-600' : 'bg-slate-100 text-slate-500'">{{ t.score }}</span>
                <span class="font-medium">{{ t.name }}</span>
                <span class="text-muted">可用配额 {{ t.avail }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="space-y-5">
          <!-- 陈旧提醒 -->
          <div class="bg-white rounded-xl border border-amber-200 p-5">
            <div class="text-sm font-bold text-amber-600 mb-3">陈旧信息提醒(>3 天未更新)</div>
            <div v-if="!report.content.stale.length" class="text-[13px] text-muted">暂无:所有需求与供货方信息均较新</div>
            <div v-for="s in report.content.stale" :key="s.type + s.name" class="text-[13px] border-b border-line last:border-0 py-2">
              <span class="px-1.5 py-0.5 rounded text-xs" :class="s.type === '需求' ? 'bg-blue-50 text-blue-600' : 'bg-slate-100 text-slate-600'">{{ s.type }}</span>
              <span class="font-medium ml-2">{{ s.name }}</span>
              <span class="text-red-500 ml-2">{{ s.days }} 天</span>
            </div>
          </div>
          <!-- 风险提示 -->
          <div class="bg-white rounded-xl border border-red-200 p-5">
            <div class="text-sm font-bold text-red-500 mb-3">风险与到期提醒</div>
            <div v-if="!report.content.risks.length" class="text-[13px] text-muted">暂无风险</div>
            <div v-for="r in report.content.risks" :key="r.detail" class="text-[13px] border-b border-line last:border-0 py-2">
              <span class="px-1.5 py-0.5 rounded text-xs bg-red-50 text-red-600">{{ r.type }}</span>
              <span class="ml-2">{{ r.detail }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 历史 -->
      <div class="bg-white rounded-xl border border-line">
        <div class="px-5 py-3.5 border-b border-line text-sm font-bold">历史简报</div>
        <table class="w-full text-[13px]">
          <tbody>
            <tr v-for="h in history" :key="h.id" class="border-b border-line last:border-0 hover:bg-slate-50/60 cursor-pointer" @click="report = h">
              <td class="px-5 py-2.5 text-muted whitespace-nowrap">{{ fmt(h.created_at) }}</td>
              <td class="px-5 py-2.5 truncate max-w-[420px]">{{ h.ai_text || '(无 AI 简报)' }}</td>
              <td class="px-5 py-2.5 text-xs text-muted whitespace-nowrap">撮合 {{ h.content.matches.length }} · 陈旧 {{ h.content.stale.length }} · 风险 {{ h.content.risks.length }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <div v-else class="bg-white rounded-xl border border-line py-12 text-center text-muted text-[13px]">
      尚无简报:点击右上角「立即扫描一次」,或等待机器人每小时自动扫描
    </div>
  </div>
</template>
