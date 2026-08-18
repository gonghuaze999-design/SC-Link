<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { listAuditLogs, listLoginLogs, type AuditLogItem, type LoginLogItem } from '../api/audit'
import { errMsg } from '../api/http'

const tab = ref<'audit' | 'login'>('audit')
const auditLogs = ref<AuditLogItem[]>([])
const loginLogs = ref<LoginLogItem[]>([])
const keyword = ref('')
const action = ref('')
const loading = ref(false)
const expanded = ref<number | null>(null)

async function load() {
  loading.value = true
  try {
    if (tab.value === 'audit') {
      auditLogs.value = await listAuditLogs({
        keyword: keyword.value,
        action: action.value,
        limit: 100,
      })
    } else {
      loginLogs.value = await listLoginLogs({ limit: 100 })
    }
  } catch (e) {
    alert(errMsg(e))
  } finally {
    loading.value = false
  }
}
onMounted(load)

const actionMeta: Record<string, { label: string; cls: string }> = {
  login: { label: '登录', cls: 'bg-slate-100 text-slate-600' },
  create: { label: '创建', cls: 'bg-green-50 text-green-600' },
  update: { label: '更新', cls: 'bg-blue-50 text-blue-600' },
  delete: { label: '删除', cls: 'bg-red-50 text-red-600' },
}

function fmtTime(t: string) {
  return t ? t.replace('T', ' ').slice(0, 19) : ''
}
function jsonText(v: Record<string, unknown> | null) {
  if (!v) return '—'
  return JSON.stringify(v, null, 2)
}
</script>

<template>
  <div>
    <div class="bg-white rounded-xl border border-line">
      <div class="flex items-center gap-3 p-4 border-b border-line">
        <div class="flex gap-1 bg-slate-100 rounded-lg p-1">
          <button
            class="px-4 py-1.5 rounded-md text-[13px] transition"
            :class="tab === 'audit' ? 'bg-white shadow text-navy font-medium' : 'text-muted'"
            @click="tab = 'audit'; expanded = null; load()"
          >
            操作日志
          </button>
          <button
            class="px-4 py-1.5 rounded-md text-[13px] transition"
            :class="tab === 'login' ? 'bg-white shadow text-navy font-medium' : 'text-muted'"
            @click="tab = 'login'; load()"
          >
            登录日志
          </button>
        </div>
        <template v-if="tab === 'audit'">
          <input
            v-model="keyword"
            class="w-52 border border-line rounded-lg px-3.5 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            placeholder="搜索操作人/对象/详情"
            @keyup.enter="load"
          />
          <select
            v-model="action"
            class="border border-line rounded-lg px-3.5 py-2.5 text-sm outline-none focus:border-primary bg-white text-muted"
            @change="load"
          >
            <option value="">全部动作</option>
            <option value="login">登录</option>
            <option value="create">创建</option>
            <option value="update">更新</option>
            <option value="delete">删除</option>
          </select>
          <button
            class="px-5 py-2.5 rounded-lg text-[13px] border border-line text-muted hover:bg-slate-50 transition"
            @click="load"
          >
            搜索
          </button>
        </template>
        <div class="ml-auto text-xs text-muted">日志只增不改,管理员亦不可删除</div>
      </div>

      <!-- 操作日志 -->
      <table v-if="tab === 'audit'" class="w-full text-sm">
        <thead>
          <tr class="text-left text-muted text-[13px] border-b border-line">
            <th class="px-5 py-3.5 font-medium">时间</th>
            <th class="px-5 py-3.5 font-medium">操作人</th>
            <th class="px-5 py-3.5 font-medium">动作</th>
            <th class="px-5 py-3.5 font-medium">对象</th>
            <th class="px-5 py-3.5 font-medium">详情</th>
            <th class="px-5 py-3.5 font-medium">IP</th>
            <th class="px-5 py-3.5 font-medium"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading" class="border-b border-line">
            <td colspan="7" class="px-4 py-8 text-center text-muted">加载中…</td>
          </tr>
          <tr v-else-if="!auditLogs.length" class="border-b border-line">
            <td colspan="7" class="px-4 py-8 text-center text-muted">暂无日志</td>
          </tr>
          <template v-for="log in auditLogs" :key="log.id">
            <tr class="border-b border-line hover:bg-slate-50/60 transition">
              <td class="px-5 py-3 text-muted whitespace-nowrap">{{ fmtTime(log.created_at) }}</td>
              <td class="px-5 py-3 font-medium">{{ log.username || '—' }}</td>
              <td class="px-5 py-3">
                <span
                  class="text-xs px-2 py-0.5 rounded"
                  :class="actionMeta[log.action]?.cls || 'bg-slate-100 text-slate-600'"
                  >{{ actionMeta[log.action]?.label || log.action }}</span
                >
              </td>
              <td class="px-5 py-3 text-muted">
                {{ log.entity_type ? `${log.entity_type}#${log.entity_id}` : '—' }}
              </td>
              <td class="px-5 py-3">{{ log.detail || '—' }}</td>
              <td class="px-5 py-3 text-muted">{{ log.ip }}</td>
              <td class="px-5 py-3 text-right">
                <button
                  v-if="log.old_value || log.new_value"
                  class="text-[13px] text-primary hover:underline"
                  @click="expanded = expanded === log.id ? null : log.id"
                >
                  {{ expanded === log.id ? '收起差异' : '查看差异' }}
                </button>
              </td>
            </tr>
            <tr v-if="expanded === log.id" class="border-b border-line bg-slate-50">
              <td colspan="7" class="px-6 py-4">
                <div class="grid grid-cols-2 gap-4">
                  <div>
                    <div class="text-xs text-muted mb-1.5">改前值</div>
                    <pre class="text-[13px] bg-white border border-line rounded-lg p-3 overflow-x-auto whitespace-pre-wrap">{{ jsonText(log.old_value) }}</pre>
                  </div>
                  <div>
                    <div class="text-xs text-muted mb-1.5">改后值</div>
                    <pre class="text-[13px] bg-white border border-line rounded-lg p-3 overflow-x-auto whitespace-pre-wrap">{{ jsonText(log.new_value) }}</pre>
                  </div>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>

      <!-- 登录日志 -->
      <table v-else class="w-full text-sm">
        <thead>
          <tr class="text-left text-muted text-[13px] border-b border-line">
            <th class="px-5 py-3.5 font-medium">时间</th>
            <th class="px-5 py-3.5 font-medium">账号</th>
            <th class="px-5 py-3.5 font-medium">结果</th>
            <th class="px-5 py-3.5 font-medium">详情</th>
            <th class="px-5 py-3.5 font-medium">IP</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading" class="border-b border-line">
            <td colspan="5" class="px-4 py-8 text-center text-muted">加载中…</td>
          </tr>
          <tr v-else-if="!loginLogs.length" class="border-b border-line">
            <td colspan="5" class="px-4 py-8 text-center text-muted">暂无日志</td>
          </tr>
          <tr v-for="log in loginLogs" :key="log.id" class="border-b border-line hover:bg-slate-50/60 transition">
            <td class="px-5 py-3 text-muted whitespace-nowrap">{{ fmtTime(log.created_at) }}</td>
            <td class="px-5 py-3 font-medium">{{ log.username }}</td>
            <td class="px-5 py-3">
              <span
                class="text-xs px-2 py-0.5 rounded"
                :class="
                  log.result === 'success'
                    ? 'bg-green-50 text-green-600'
                    : log.result === 'lockout'
                      ? 'bg-amber-50 text-amber-600'
                      : 'bg-red-50 text-red-600'
                "
                >{{ log.result === 'success' ? '成功' : log.result === 'lockout' ? '锁定' : '失败' }}</span
              >
            </td>
            <td class="px-5 py-3 text-muted">{{ log.detail || '—' }}</td>
            <td class="px-5 py-3 text-muted">{{ log.ip }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
