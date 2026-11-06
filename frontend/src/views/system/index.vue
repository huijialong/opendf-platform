<script setup>
import { onMounted, ref } from 'vue'
import { listUsers } from '@/api/modules'

const loading = ref(false)
const error = ref('')
const users = ref([])

const roles = [
  { name: '超级管理员', duty: '管理设备、任务、配置和账号，能导出全部标准包。' },
  { name: '采集人员', duty: '登记设备、上传会话，或生成模拟样本。' },
  { name: '标注与质检员', duty: '在时间轴上打动作标签，并执行通过或驳回。' },
]

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await listUsers()
    users.value = res.data.items
  } catch (err) {
    error.value = err?.message || '用户列表加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div v-loading="loading">
    <div class="page-head">
      <div>
        <h2>系统管理</h2>
        <p>演示环境预置三类角色。在右上角切换身份时，密码都是 opendf。</p>
      </div>
    </div>
    <el-alert v-if="error" type="error" :title="error" show-icon class="gap">
      <el-button size="small" @click="load">重试</el-button>
    </el-alert>
    <div class="roles">
      <article v-for="role in roles" :key="role.name" class="odf-card role">
        <h3>{{ role.name }}</h3>
        <p>{{ role.duty }}</p>
      </article>
    </div>
    <section class="odf-card block">
      <div class="table-wrap">
        <el-table :data="users" empty-text="没有用户">
          <el-table-column prop="username" label="账号" width="140" />
          <el-table-column prop="name" label="姓名" width="140" />
          <el-table-column prop="role" label="角色" min-width="160" />
          <el-table-column prop="status" label="状态" width="100" />
          <el-table-column label="密码" width="120">
            <template #default>opendf</template>
          </el-table-column>
        </el-table>
      </div>
    </section>
  </div>
</template>

<style scoped>
.gap { margin-bottom: 12px; }
.roles { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 16px; }
.role, .block { padding: 16px; }
.role h3 { margin: 0 0 8px; }
.role p { margin: 0; color: #606266; line-height: 1.6; }
@media (max-width: 800px) {
  .roles { grid-template-columns: 1fr; }
}
</style>
