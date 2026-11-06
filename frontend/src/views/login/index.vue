<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login } from '@/api/modules'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)
const form = reactive({ username: 'admin', password: 'opendf' })

const presets = [
  { username: 'admin', name: '超级管理员' },
  { username: 'collector', name: '采集人员' },
  { username: 'qa', name: '标注与质检员' },
]

function usePreset(username) {
  form.username = username
  form.password = 'opendf'
}

async function submit() {
  loading.value = true
  try {
    const res = await login(form)
    userStore.setUser(res.data.user, res.data.token)
    ElMessage.success(`欢迎，${res.data.user.name}`)
    router.push('/dashboard')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login">
    <section class="panel">
      <div class="brand">
        <strong>具身采标平台</strong>
        <em>DATA FUSION</em>
      </div>
      <h1>登录 OpenDF</h1>
      <p>本地演示账号密码均为 opendf。</p>
      <div class="presets">
        <button v-for="item in presets" :key="item.username" type="button" @click="usePreset(item.username)">
          {{ item.name }}
        </button>
      </div>
      <el-form @submit.prevent="submit">
        <el-form-item>
          <el-input v-model="form.username" placeholder="账号" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" type="password" show-password placeholder="密码" />
        </el-form-item>
        <el-button type="primary" :loading="loading" style="width: 100%" @click="submit">进入平台</el-button>
      </el-form>
    </section>
  </div>
</template>

<style scoped>
.login {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background:
    radial-gradient(circle at top left, rgba(24, 144, 255, 0.35), transparent 42%),
    #304156;
  padding: 24px;
}

.panel {
  width: min(420px, 100%);
  background: #fff;
  border-radius: 12px;
  padding: 28px 28px 24px;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.18);
}

.brand {
  display: flex;
  flex-direction: column;
  margin-bottom: 12px;
}

.brand strong { font-size: 18px; color: #1f2d3d; }
.brand em { color: #1890ff; font-style: normal; letter-spacing: 1px; font-size: 12px; }

h1 { margin: 0 0 6px; font-size: 22px; }
p { margin: 0 0 14px; color: #909399; }

.presets { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
.presets button {
  border: 1px solid #d9ecff;
  background: #f4f9ff;
  color: #1890ff;
  border-radius: 16px;
  padding: 4px 10px;
  cursor: pointer;
}
</style>
