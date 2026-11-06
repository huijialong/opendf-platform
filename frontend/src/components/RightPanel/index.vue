<script setup>
import { ref } from 'vue'
import { useSettingsStore } from '@/stores/settings'

const open = ref(false)
const settings = useSettingsStore()
const colors = ['#1890ff', '#304156', '#13c2c2', '#722ed1', '#f5222d', '#52c41a']
</script>

<template>
  <button v-show="!open" class="setting-trigger" type="button" aria-label="布局设置" @click="open = true">
    <el-icon :size="20"><Setting /></el-icon>
  </button>
  <el-drawer v-model="open" title="布局设置" direction="rtl" size="300px" append-to-body>
    <div class="setting-block">
      <span>暗黑模式</span>
      <el-switch v-model="settings.darkMode" />
    </div>
    <div class="setting-block column">
      <span>导航主题色</span>
      <div class="swatches">
        <button
          v-for="color in colors"
          :key="color"
          type="button"
          class="swatch"
          :class="{ active: settings.themeColor === color }"
          :style="{ background: color }"
          :aria-label="color"
          @click="settings.themeColor = color"
        />
      </div>
    </div>
    <div class="setting-block">
      <span>固定顶栏</span>
      <el-switch v-model="settings.fixedHeader" />
    </div>
    <div class="setting-block">
      <span>显示标签栏</span>
      <el-switch v-model="settings.showTagsView" />
    </div>
    <div class="setting-block column">
      <span>字号</span>
      <el-radio-group v-model="settings.fontSize">
        <el-radio-button value="large">较大</el-radio-button>
        <el-radio-button value="default">默认</el-radio-button>
        <el-radio-button value="small">紧凑</el-radio-button>
      </el-radio-group>
    </div>
    <el-button @click="settings.reset()">恢复默认</el-button>
  </el-drawer>
</template>

<style scoped>
.setting-trigger {
  position: fixed;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 44px;
  height: 44px;
  background: #1890ff;
  border-radius: 6px 0 0 6px;
  border: none;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 2001;
  box-shadow: -2px 0 8px rgba(24, 144, 255, 0.35);
}

.setting-trigger:hover {
  background: #40a9ff;
}

.setting-block {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
  color: #303133;
}

.setting-block.column {
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
}

.swatches {
  display: flex;
  gap: 8px;
}

.swatch {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  border: 2px solid transparent;
  cursor: pointer;
}

.swatch.active {
  border-color: #1f2d3d;
}
</style>
