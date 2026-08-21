<script setup lang="ts">
import { ref } from 'vue'
import SuppliersTab from './entities/SuppliersTab.vue'
import CustomersTab from './entities/CustomersTab.vue'
import MiddlesTab from './entities/MiddlesTab.vue'
import ChainsTab from './entities/ChainsTab.vue'

const tabs = [
  { key: 'chains', label: '海外链路方' },
  { key: 'suppliers', label: '上游供货方' },
  { key: 'customers', label: '下游客户' },
  { key: 'middles', label: '中间层' },
]
const active = ref('chains')
</script>

<template>
  <div>
    <div class="flex gap-1 bg-white rounded-xl border border-line p-1.5 w-fit mb-6">
      <button
        v-for="t in tabs"
        :key="t.key"
        class="px-6 py-2.5 rounded-lg text-sm transition whitespace-nowrap"
        :class="active === t.key ? 'bg-primary text-white shadow' : 'text-muted hover:text-navy'"
        @click="active = t.key"
      >
        {{ t.label }}
      </button>
    </div>
    <ChainsTab v-if="active === 'chains'" />
    <SuppliersTab v-else-if="active === 'suppliers'" />
    <CustomersTab v-else-if="active === 'customers'" />
    <MiddlesTab v-else />
  </div>
</template>
