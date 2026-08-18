<script setup lang="ts">
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()

const kpis = [
  { label: '上游供货方', value: '--', hint: '主体管理上线后可维护' },
  { label: '下游客户', value: '--', hint: '主体管理上线后可维护' },
  { label: '在途订单', value: '--', hint: '订单跟踪上线后统计' },
  { label: '本月成交额', value: '--', hint: '订单跟踪上线后统计' },
]
</script>

<template>
  <div>
    <div class="bg-white rounded-xl border border-line p-8 mb-6">
      <h2 class="text-xl font-bold">你好,{{ auth.user?.display_name || auth.user?.username }}</h2>
      <p class="text-[13px] text-muted mt-2">
        阶段一开发中:用户体系、登录锁定与审计日志已可用;主体管理、数据共享、供需看板等模块将陆续上线。
      </p>
    </div>
    <div class="grid grid-cols-4 gap-5">
      <div v-for="k in kpis" :key="k.label" class="bg-white rounded-xl border border-line p-6">
        <div class="text-[13px] text-muted">{{ k.label }}</div>
        <div class="text-3xl font-bold mt-3" style="font-variant-numeric: tabular-nums">
          {{ k.value }}
        </div>
        <div class="text-xs text-muted mt-1.5">{{ k.hint }}</div>
      </div>
    </div>
  </div>
</template>
