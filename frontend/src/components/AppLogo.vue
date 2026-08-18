<script setup lang="ts">
defineProps<{ size?: number }>()
</script>

<template>
  <svg
    :width="size || 40"
    :height="size || 40"
    viewBox="0 0 48 48"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <defs>
      <linearGradient id="logo-bg" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="#0F172A" />
        <stop offset="1" stop-color="#1E3A8A" />
      </linearGradient>
      <linearGradient id="logo-core" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="#2563EB" />
        <stop offset="1" stop-color="#06B6D4" />
      </linearGradient>
    </defs>

    <!-- 底板(深空蓝) -->
    <rect x="1" y="1" width="46" height="46" rx="12" fill="url(#logo-bg)" />

    <!-- 算力芯片主体 -->
    <rect x="11.5" y="11.5" width="25" height="25" rx="3.5" stroke="url(#logo-core)" stroke-width="2" />

    <!-- 芯片引脚(上下左右,算力接口) -->
    <path d="M17 11.5V8.5 M24 11.5V8.5 M31 11.5V8.5" stroke="#64748B" stroke-width="1.8" stroke-linecap="round" />
    <path d="M17 36.5V39.5 M24 36.5V39.5 M31 36.5V39.5" stroke="#64748B" stroke-width="1.8" stroke-linecap="round" />
    <path d="M11.5 17H8.5 M11.5 24H8.5 M11.5 31H8.5" stroke="#64748B" stroke-width="1.8" stroke-linecap="round" />
    <path d="M36.5 17H39.5 M36.5 24H39.5 M36.5 31H39.5" stroke="#64748B" stroke-width="1.8" stroke-linecap="round" />

    <!-- 电路走线汇入核心 -->
    <path d="M11.5 24H19 M29 24H36.5 M24 11.5V19 M24 29V36.5" stroke="#06B6D4" stroke-width="1.4" stroke-opacity="0.7" />
    <path d="M15 15L19 19 M33 15L29 19 M15 33L19 29 M33 33L29 29" stroke="#06B6D4" stroke-width="1.2" stroke-opacity="0.4" />

    <!-- AI 神经核心(发光) -->
    <circle cx="24" cy="24" r="7.5" fill="#06B6D4" fill-opacity="0.12" />
    <circle cx="24" cy="24" r="3.2" fill="url(#logo-core)" />
    <circle cx="24" cy="24" r="5.4" stroke="#06B6D4" stroke-width="1" stroke-opacity="0.6" />

    <!-- 神经突触节点 -->
    <circle cx="18" cy="18" r="1.6" fill="#93C5FD" />
    <circle cx="30" cy="18" r="1.6" fill="#93C5FD" />
    <circle cx="18" cy="30" r="1.6" fill="#93C5FD" />
    <circle cx="30" cy="30" r="1.6" fill="#93C5FD" />
    <path d="M18 18L22 20 M30 18L26 20 M18 30L22 28 M30 30L26 28" stroke="#93C5FD" stroke-width="1" stroke-opacity="0.7" />

    <!-- AI 星光(右上角火花) -->
    <path d="M37 9.5L38 12.5L41 13.5L38 14.5L37 17.5L36 14.5L33 13.5L36 12.5Z" fill="#22D3EE" />
  </svg>
</template>
