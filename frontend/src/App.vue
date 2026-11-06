<script setup>
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import { useSettingsStore } from '@/stores/settings'

const settings = useSettingsStore()
</script>

<template>
  <el-config-provider :locale="zhCn" :size="settings.fontSize">
    <router-view />
  </el-config-provider>
</template>
