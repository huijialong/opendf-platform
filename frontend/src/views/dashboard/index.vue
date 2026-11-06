<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getStats } from '@/api/modules'
import { taskStatus } from '@/utils/dict'
import { formatDate } from '@/utils/format'

const router = useRouter()
const loading = ref(true)
const error = ref('')
const stats = ref(null)

const stepIcons = ['VideoCamera', 'Upload', 'FolderOpened', 'EditPen', 'CircleCheck', 'Coin']

const cards = computed(() => {
  const data = stats.value || {}
  return [
    { key: 'device', label: '采集设备数', value: data.device_count ?? '—', foot: '平台接入的本体、夹爪与头显', icon: 'Monitor', tint: '#e6f4ff', color: '#1890ff' },
    { key: 'storage', label: '存储占用容量', value: data.storage_formatted ?? '—', foot: '原始域与标准域合计', icon: 'Coin', tint: '#e6fffb', color: '#13c2c2' },
    { key: 'tasks', label: '进行中标注任务', value: data.active_tasks ?? '—', foot: '采集、清洗、标注与审核', icon: 'EditPen', tint: '#fff7e6', color: '#fa8c16' },
    { key: 'datasets', label: '标准数据集总数', value: data.dataset_count ?? '—', foot: '可导出 LeRobot / HDF5', icon: 'FolderOpened', tint: '#f9f0ff', color: '#722ed1' },
  ]
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await getStats()
    stats.value = res.data
  } catch (err) {
    error.value = err?.message || '看板数据加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div v-loading="loading" class="dashboard">
    <el-alert v-if="error" type="error" :title="error" show-icon :closable="false" class="gap">
      <el-button size="small" @click="load">重试</el-button>
    </el-alert>

    <section class="odf-card flow-panel">
      <div class="flow-head">
        <div>
          <h1>多源异构数采平台</h1>
          <p>把机械臂轨迹、VR 第一视角和触觉数据收成同一条时间轴，再交付可训练的标准数据集。</p>
        </div>
        <el-tag type="success" effect="plain">本地闭环 · SQLite</el-tag>
      </div>
      <div class="steps">
        <article v-for="(step, index) in stats?.pipeline_steps || []" :key="step.step" class="step">
          <div class="step-index">{{ String(step.step).padStart(2, '0') }}</div>
          <div class="step-copy">
            <div class="step-name">
              <el-icon><component :is="stepIcons[index]" /></el-icon>
              {{ step.name }}
            </div>
            <p>{{ step.desc }}</p>
          </div>
        </article>
      </div>
    </section>

    <section class="metrics">
      <article v-for="card in cards" :key="card.key" class="odf-card metric">
        <div class="metric-icon" :style="{ background: card.tint, color: card.color }">
          <el-icon :size="28"><component :is="card.icon" /></el-icon>
        </div>
        <div>
          <div class="metric-label">{{ card.label }}</div>
          <div class="metric-value">{{ card.value }}</div>
          <div class="metric-foot">{{ card.foot }}</div>
        </div>
      </article>
    </section>

    <el-row :gutter="16" class="lower">
      <el-col :xs="24" :lg="16">
        <section class="odf-card block">
          <div class="block-head">
            <h3>最近任务</h3>
            <el-button link type="primary" @click="router.push('/task')">进入任务管理</el-button>
          </div>
          <div class="table-wrap">
            <el-table :data="stats?.recent_tasks || []" empty-text="还没有任务">
              <el-table-column prop="task_code" label="编号" min-width="140" />
              <el-table-column prop="title" label="任务" min-width="160" />
              <el-table-column prop="assignee" label="负责人" width="100">
                <template #default="{ row }">{{ row.assignee || '未分配' }}</template>
              </el-table-column>
              <el-table-column label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="taskStatus(row.status).type" size="small">{{ taskStatus(row.status).label }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="进度" min-width="140">
                <template #default="{ row }">
                  <el-progress :percentage="row.progress" :stroke-width="8" />
                </template>
              </el-table-column>
            </el-table>
          </div>
        </section>
      </el-col>
      <el-col :xs="24" :lg="8">
        <section class="odf-card block">
          <div class="block-head">
            <h3>最新动态</h3>
          </div>
          <el-empty v-if="!(stats?.activities || []).length" description="生成一条模拟样本后，这里会出现入库记录" :image-size="72" />
          <el-timeline v-else>
            <el-timeline-item v-for="(item, index) in stats.activities" :key="index" :timestamp="formatDate(item.time)">
              {{ item.text }}
            </el-timeline-item>
          </el-timeline>
        </section>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.gap { margin-bottom: 12px; }

.flow-panel { padding: 20px 20px 8px; margin-bottom: 16px; }

.flow-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 18px;
}

.flow-head h1 {
  margin: 0 0 6px;
  font-size: 26px;
  letter-spacing: 0.5px;
  color: #1f2d3d;
}

.flow-head p {
  margin: 0;
  color: #606266;
  max-width: 680px;
  line-height: 1.6;
}

.steps {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 8px;
  position: relative;
  padding-bottom: 12px;
}

.steps::before {
  content: "";
  position: absolute;
  top: 18px;
  left: 6%;
  right: 6%;
  height: 2px;
  background: linear-gradient(90deg, #bae0ff, #1890ff);
}

.step { position: relative; text-align: center; padding: 0 6px 12px; }

.step-index {
  width: 36px;
  height: 36px;
  margin: 0 auto 10px;
  border-radius: 50%;
  background: #1890ff;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  position: relative;
  z-index: 1;
  box-shadow: 0 0 0 4px #fff;
}

.step-name {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  font-weight: 650;
  color: #1f2d3d;
  margin-bottom: 4px;
}

.step-copy p {
  margin: 0;
  color: #909399;
  font-size: 12px;
  line-height: 1.45;
  min-height: 34px;
}

.metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.metric {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 22px 20px;
  min-height: 124px;
  border-top: 3px solid var(--odf-primary, #1890ff);
}

.metric-icon {
  width: 64px;
  height: 64px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}

.metric-label { color: #909399; font-size: 14px; }
.metric-value {
  margin: 4px 0;
  font-size: 36px;
  line-height: 1.1;
  font-weight: 700;
  color: #1f2d3d;
  font-variant-numeric: tabular-nums;
}
.metric-foot { color: #c0c4cc; font-size: 12px; }

.lower { margin-top: 16px; }
.block { padding: 16px; min-height: 280px; }
.block-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.block-head h3 { margin: 0; font-size: 16px; }

@media (max-width: 1100px) {
  .metrics { grid-template-columns: repeat(2, 1fr); }
  .steps { grid-template-columns: repeat(3, 1fr); row-gap: 16px; }
  .steps::before { display: none; }
}

@media (max-width: 640px) {
  .flow-head { flex-direction: column; }
  .flow-head h1 { font-size: 22px; }
  .metrics, .steps { grid-template-columns: 1fr; }
  .step { text-align: left; display: grid; grid-template-columns: 44px 1fr; column-gap: 8px; }
  .step-index { margin: 0; }
  .metric-value { font-size: 30px; }
}
</style>
