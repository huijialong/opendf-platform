<script setup>
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useFullscreen } from '@vueuse/core'
import { ElMessage } from 'element-plus'
import { useSettingsStore } from '@/stores/settings'
import { useUserStore } from '@/stores/user'
import { login } from '@/api/modules'

const route = useRoute()
const router = useRouter()
const settings = useSettingsStore()
const userStore = useUserStore()
const { isFullscreen, toggle } = useFullscreen()

const crumbs = computed(() => {
  const items = [{ title: '首页', to: '/dashboard' }]
  if (route.path === '/dashboard') return items
  if (route.meta.group) items.push({ title: route.meta.group })
  items.push({ title: route.meta.title || '' })
  return items
})

const notices = [
  { title: 'TSK-2026-003 布料折叠进入待审核', time: '今天 09:24' },
  { title: 'UMI-001 标定内参已回写', time: '今天 08:10' },
  { title: '标准域导出队列空闲', time: '昨天 18:40' },
]

const switchOpen = ref(false)
const switching = ref(false)
const form = reactive({ username: 'admin', password: 'opendf' })

const accounts = [
  { username: 'admin', label: '超级管理员' },
  { username: 'collector', label: '采集人员' },
  { username: 'qa', label: '标注与质检员' },
]

function pickAccount(username) {
  form.username = username
  form.password = 'opendf'
}

async function submitSwitch() {
  switching.value = true
  try {
    const res = await login({ username: form.username, password: form.password })
    userStore.setUser(res.data.user, res.data.token)
    switchOpen.value = false
    ElMessage.success(`已切换为${res.data.user.role}`)
  } finally {
    switching.value = false
  }
}

function logout() {
  userStore.logout()
  router.push('/login')
}
</script>

<template>
  <header class="navbar">
    <div class="nav-left">
      <button class="tool-btn" type="button" aria-label="折叠侧边栏" @click="settings.toggleSidebar()">
        <el-icon><Fold v-if="!settings.sidebarCollapsed" /><Expand v-else /></el-icon>
      </button>
      <el-breadcrumb separator="/">
        <el-breadcrumb-item v-for="item in crumbs" :key="item.title" :to="item.to">
          {{ item.title }}
        </el-breadcrumb-item>
      </el-breadcrumb>
    </div>
    <div class="nav-right">
      <button class="tool-btn" type="button" :aria-label="isFullscreen ? '退出全屏' : '全屏'" @click="toggle">
        <el-icon><CloseBold v-if="isFullscreen" /><FullScreen v-else /></el-icon>
      </button>
      <el-dropdown trigger="click" @command="settings.fontSize = $event">
        <button class="tool-btn" type="button" aria-label="字号">
          <span class="tt-mark">Tt</span>
        </button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="large" :disabled="settings.fontSize === 'large'">较大</el-dropdown-item>
            <el-dropdown-item command="default" :disabled="settings.fontSize === 'default'">默认</el-dropdown-item>
            <el-dropdown-item command="small" :disabled="settings.fontSize === 'small'">紧凑</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
      <el-popover placement="bottom-end" :width="300" trigger="click">
        <template #reference>
          <button class="tool-btn" type="button" aria-label="消息">
            <el-icon><Bell /></el-icon>
          </button>
        </template>
        <div class="msg-list">
          <div v-for="item in notices" :key="item.title" class="msg-item">
            <strong>{{ item.title }}</strong>
            <span>{{ item.time }}</span>
          </div>
        </div>
      </el-popover>
      <el-dropdown trigger="click">
        <span class="user-entry">
          <el-avatar :size="28" style="background: #1890ff">{{ (userStore.profile.name || '用').slice(0, 1) }}</el-avatar>
          <span class="user-name">{{ userStore.profile.name }}</span>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item disabled>{{ userStore.profile.role || '未登录' }}</el-dropdown-item>
            <el-dropdown-item @click="switchOpen = true">切换身份</el-dropdown-item>
            <el-dropdown-item divided @click="logout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>

    <el-dialog v-model="switchOpen" title="切换身份" width="420px">
      <p class="switch-tip">演示账号密码均为 <code>opendf</code>。</p>
      <div class="account-picks">
        <el-button v-for="item in accounts" :key="item.username" @click="pickAccount(item.username)">
          {{ item.label }}
        </el-button>
      </div>
      <el-form label-width="72px" @submit.prevent="submitSwitch">
        <el-form-item label="账号">
          <el-input v-model="form.username" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="switchOpen = false">取消</el-button>
        <el-button type="primary" :loading="switching" @click="submitSwitch">登录</el-button>
      </template>
    </el-dialog>
  </header>
</template>

<style scoped>
.switch-tip {
  margin: 0 0 12px;
  color: #909399;
  font-size: 13px;
}

.account-picks {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 14px;
}

code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
</style>
