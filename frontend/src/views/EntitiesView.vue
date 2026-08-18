<script setup lang="ts">
import { ref } from 'vue'
import SuppliersTab from './entities/SuppliersTab.vue'
import CustomersTab from './entities/CustomersTab.vue'
import MiddlesTab from './entities/MiddlesTab.vue'
import ChainsTab from './entities/ChainsTab.vue'

const tabs = [
  { key: 'suppliers', label: '上游供货方' },
  { key: 'customers', label: '下游客户' },
  { key: 'middles', label: '中间层' },
  { key: 'chains', label: '海外链路方' },
]
const active = ref('suppliers')
</script>

<template>
  <div>
    <div class="flex gap-1 bg-white rounded-xl border border-line p-1 w-fit mb-5">
      <button
        v-for="t in tabs"
        :key="t.key"
        class="px-5 py-2 rounded-lg text-[13px] transition"
        :class="active === t.key ? 'bg-primary text-white shadow' : 'text-muted hover:text-navy'"
        @click="active = t.key"
      >
        {{ t.label }}
      </button>
    </div>
    <SuppliersTab v-if="active === 'suppliers'" />
    <CustomersTab v-else-if="active === 'customers'" />
    <MiddlesTab v-else-if="active === 'middles'" />
    <ChainsTab v-else />
  </div>
</template>
