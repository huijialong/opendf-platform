<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useSettingsStore } from '@/stores/settings'

const route = useRoute()
const settings = useSettingsStore()
const active = computed(() => route.path)
const desktop = ref(true)

function sync() {
  desktop.value = window.innerWidth > 992
}

onMounted(() => {
  sync()
  window.addEventListener('resize', sync)
})
onBeforeUnmount(() => window.removeEventListener('resize', sync))
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar-logo">
      <svg class="logo-mark" viewBox="0 0 32 32" aria-hidden="true">
        <rect width="32" height="32" rx="7" fill="#1890ff" />
        <path d="M8 23V9h5.2a5.2 5.2 0 0 1 0 10.4H8" fill="none" stroke="#fff" stroke-width="2.2" />
        <path d="M19 11h6M19 16h4.5M19 21h6" stroke="#fff" stroke-width="2.1" stroke-linecap="round" />
      </svg>
      <div class="logo-text">
        <strong>具身采标平台</strong>
        <em>DATA FUSION</em>
      </div>
    </div>
    <div class="sidebar-scroll">
      <el-menu
        :default-active="active"
        :collapse="settings.sidebarCollapsed && desktop"
        :collapse-transition="false"
        :default-openeds="['capture-group']"
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#ffffff"
        router
      >
        <el-menu-item index="/dashboard">
          <el-icon><HomeFilled /></el-icon>
          <template #title>首页</template>
        </el-menu-item>
        <el-menu-item index="/task">
          <el-icon><List /></el-icon>
          <template #title>任务管理</template>
        </el-menu-item>
        <el-sub-menu index="capture-group">
          <template #title>
            <el-icon><VideoCamera /></el-icon>
            <span>采集模块</span>
          </template>
          <el-menu-item index="/device">设备登记</el-menu-item>
          <el-menu-item index="/capture">采集会话</el-menu-item>
        </el-sub-menu>
        <el-menu-item index="/annotation">
          <el-icon><EditPen /></el-icon>
          <template #title>标注模块</template>
        </el-menu-item>
        <el-menu-item index="/review">
          <el-icon><CircleCheck /></el-icon>
          <template #title>审核模块</template>
        </el-menu-item>
        <el-menu-item index="/dataset">
          <el-icon><Coin /></el-icon>
          <template #title>数据模块</template>
        </el-menu-item>
        <el-menu-item index="/config">
          <el-icon><Setting /></el-icon>
          <template #title>配置管理</template>
        </el-menu-item>
        <el-menu-item index="/system">
          <el-icon><Tools /></el-icon>
          <template #title>系统管理</template>
        </el-menu-item>
        <el-menu-item index="/docs">
          <el-icon><Document /></el-icon>
          <template #title>操作手册</template>
        </el-menu-item>
      </el-menu>
    </div>
  </aside>
</template>
