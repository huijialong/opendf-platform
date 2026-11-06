<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { exportDataset, listExports, listSessions, listTasks } from '@/api/modules'
import { formatBytes } from '@/utils/format'

const loading = ref(false)
const exporting = ref(false)
const error = ref('')
const tasks = ref([])
const history = ref([])
const taskId = ref(null)
const format = ref('lerobot')
const result = ref(null)

const formats = [
  { value: 'lerobot', title: 'LeRobot', desc: 'meta/info.json、episodes 与逐帧 CSV，可直接对接训练仓库。' },
  { value: 'hdf5', title: 'HDF5 结构', desc: '按 /observations、/actions、/timestamps 组路径打包数组与视频。' },
  { value: 'json', title: 'JSON', desc: '任务、回合和标注切片的可读索引。' },
]

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [taskRes, exportRes, sessionRes] = await Promise.all([
      listTasks({ page: 1, page_size: 100 }),
      listExports(),
      listSessions({ page: 1, page_size: 20 }),
    ])
    tasks.value = taskRes.data.items
    history.value = exportRes.data.items
    if (!taskId.value) {
      const withSession = sessionRes.data.items.find((item) => item.task_id)
      taskId.value = withSession?.task_id || tasks.value[0]?.id || null
    }
  } catch (err) {
    error.value = err?.message || '数据集页面加载失败'
  } finally {
    loading.value = false
  }
}

async function runExport() {
  if (!taskId.value) {
    ElMessage.warning('请选择任务')
    return
  }
  exporting.value = true
  result.value = null
  try {
    const res = await exportDataset({ task_id: taskId.value, format: format.value })
    result.value = res.data
    ElMessage.success(`数据包已生成，用时 ${res.data.elapsed_ms} ms`)
    const exportRes = await listExports()
    history.value = exportRes.data.items
  } catch {
    result.value = null
  } finally {
    exporting.value = false
  }
}

function stamp(value) {
  if (!value) return '—'
  return new Date(value * 1000).toLocaleString()
}

onMounted(load)
</script>

<template>
  <div v-loading="loading">
    <div class="page-head">
      <div>
        <h2>数据模块</h2>
        <p>原始数据只读留在 origin，清洗对齐后的标准表进入 std，再按 LeRobot 或 HDF5 结构导出。</p>
      </div>
    </div>
    <el-alert v-if="error" type="error" :title="error" show-icon class="gap">
      <el-button size="small" @click="load">重试</el-button>
    </el-alert>
    <div class="domains">
      <article class="odf-card domain">
        <h3>origin 原始域</h3>
        <p>采集上传的视频和轨迹保持原样，导出包里放在 origin/，不在清洗过程中改写。</p>
      </article>
      <article class="odf-card domain">
        <h3>std 标准域</h3>
        <p>时间对齐后的末端位姿、夹爪宽度、速度和动作标签进入 data/，通过审核的切片一并打进包里。</p>
      </article>
    </div>

    <section class="odf-card block">
      <h3>导出标准包</h3>
      <el-form label-width="88px">
        <el-form-item label="任务">
          <el-select v-model="taskId" style="width: min(420px, 100%)">
            <el-option v-for="task in tasks" :key="task.id" :label="`${task.task_code} ${task.title}`" :value="task.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="格式">
          <div class="format-field">
            <el-radio-group v-model="format">
              <el-radio-button v-for="item in formats" :key="item.value" :value="item.value">{{ item.title }}</el-radio-button>
            </el-radio-group>
            <p class="format-desc">{{ formats.find((item) => item.value === format)?.desc }}</p>
          </div>
        </el-form-item>
        <el-button type="primary" :loading="exporting" @click="runExport">开始导出</el-button>
      </el-form>
      <el-alert v-if="result" type="success" show-icon :closable="false" class="result">
        <template #title>
          {{ result.filename }} · {{ formatBytes(result.size_bytes) }} · {{ result.elapsed_ms }} ms · {{ result.episode_count }} 回合
        </template>
        <el-link :href="result.download_url" target="_blank" type="primary">下载数据包</el-link>
      </el-alert>
    </section>

    <section class="odf-card block">
      <h3>导出记录</h3>
      <div class="table-wrap">
        <el-table :data="history" empty-text="还没有导出包">
          <el-table-column prop="filename" label="文件" min-width="280" />
          <el-table-column label="大小" width="120">
            <template #default="{ row }">{{ formatBytes(row.size_bytes) }}</template>
          </el-table-column>
          <el-table-column label="时间" min-width="180">
            <template #default="{ row }">{{ stamp(row.modified_at) }}</template>
          </el-table-column>
          <el-table-column label="下载" width="100">
            <template #default="{ row }">
              <el-link :href="row.download_url" target="_blank" type="primary">下载</el-link>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </section>
  </div>
</template>

<style scoped>
.gap { margin-bottom: 12px; }
.domains { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
.domain, .block { padding: 16px; }
.domain h3, .block h3 { margin: 0 0 8px; }
.domain p, .format-desc { margin: 0; color: #606266; line-height: 1.6; }
.format-field { display: flex; flex-direction: column; align-items: flex-start; gap: 8px; width: 100%; }
.block { margin-bottom: 16px; }
.format-desc { margin-top: 8px; }
.result { margin-top: 16px; }
@media (max-width: 800px) {
  .domains { grid-template-columns: 1fr; }
}
</style>
