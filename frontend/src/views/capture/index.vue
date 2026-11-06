<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { createMockSample, listDevices, listSessions, listTasks, uploadSession } from '@/api/modules'
import { formatClock, formatDate } from '@/utils/format'

const router = useRouter()
const loading = ref(false)
const error = ref('')
const mocking = ref(false)
const uploading = ref(false)
const progress = ref(0)
const items = ref([])
const total = ref(0)
const tasks = ref([])
const devices = ref([])
const videoFile = ref(null)
const trajectoryFile = ref(null)
const form = reactive({ task_id: null, device_sn: '' })

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [sessionRes, taskRes, deviceRes] = await Promise.all([
      listSessions({ page: 1, page_size: 50 }),
      listTasks({ page: 1, page_size: 100 }),
      listDevices({ page: 1, page_size: 100 }),
    ])
    items.value = sessionRes.data.items
    total.value = sessionRes.data.total
    tasks.value = taskRes.data.items
    devices.value = deviceRes.data.items
    if (!form.task_id && tasks.value.length) form.task_id = tasks.value[0].id
  } catch (err) {
    error.value = err?.message || '会话列表加载失败'
  } finally {
    loading.value = false
  }
}

async function makeSample() {
  mocking.value = true
  try {
    const res = await createMockSample({ task_id: form.task_id, device_sn: form.device_sn || null })
    ElMessage.success('已生成正弦轨迹和测试视频')
    await load()
    return res.data
  } finally {
    mocking.value = false
  }
}

function onVideo(upload) {
  videoFile.value = upload.raw
}
function onTrajectory(upload) {
  trajectoryFile.value = upload.raw
}

async function submitUpload() {
  if (!form.task_id) {
    ElMessage.warning('请选择任务')
    return
  }
  if (!videoFile.value && !trajectoryFile.value) {
    ElMessage.warning('请选择视频或轨迹文件')
    return
  }
  const body = new FormData()
  body.append('task_id', String(form.task_id))
  if (form.device_sn) body.append('device_sn', form.device_sn)
  if (videoFile.value) body.append('video_file', videoFile.value)
  if (trajectoryFile.value) body.append('trajectory_file', trajectoryFile.value)
  uploading.value = true
  progress.value = 0
  try {
    await uploadSession(body, (event) => {
      if (event.total) progress.value = Math.round((event.loaded / event.total) * 100)
    })
    ElMessage.success('会话已入库')
    videoFile.value = null
    trajectoryFile.value = null
    await load()
  } finally {
    uploading.value = false
  }
}

function annotate(row) {
  router.push({ path: '/annotation', query: { session: row.id } })
}

onMounted(load)
</script>

<template>
  <div v-loading="loading">
    <div class="page-head">
      <div>
        <h2>采集会话</h2>
        <p>上传主视角视频和机械臂轨迹，或在没有硬件时一键生成正弦夹爪样本。</p>
      </div>
      <div class="head-actions">
        <el-button type="primary" :loading="mocking" @click="makeSample">生成模拟样本</el-button>
      </div>
    </div>
    <el-alert v-if="error" type="error" :title="error" show-icon class="gap">
      <el-button size="small" @click="load">重试</el-button>
    </el-alert>

    <section class="odf-card block">
      <h3>组合上传</h3>
      <el-form label-width="88px">
        <el-row :gutter="12">
          <el-col :xs="24" :md="8">
            <el-form-item label="所属任务">
              <el-select v-model="form.task_id" style="width: 100%">
                <el-option v-for="task in tasks" :key="task.id" :label="`${task.task_code} ${task.title}`" :value="task.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="8">
            <el-form-item label="采集设备">
              <el-select v-model="form.device_sn" clearable placeholder="可选" style="width: 100%">
                <el-option v-for="device in devices" :key="device.device_sn" :label="device.name" :value="device.device_sn" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :xs="24" :md="12">
            <el-upload drag :auto-upload="false" :limit="1" accept=".mp4,.webm,.mov" :on-change="onVideo">
              <el-icon class="upload-icon"><VideoCamera /></el-icon>
              <div>拖入 RGB 主视角视频</div>
            </el-upload>
          </el-col>
          <el-col :xs="24" :md="12">
            <el-upload drag :auto-upload="false" :limit="1" accept=".json,.csv" :on-change="onTrajectory">
              <el-icon class="upload-icon"><Document /></el-icon>
              <div>拖入轨迹 JSON / CSV</div>
            </el-upload>
          </el-col>
        </el-row>
        <el-progress v-if="uploading" :percentage="progress" class="progress" />
        <el-button type="primary" :loading="uploading" @click="submitUpload">上传并建会话</el-button>
      </el-form>
    </section>

    <section class="odf-card block">
      <div class="block-head">
        <h3>会话列表</h3>
        <span>{{ total }} 条</span>
      </div>
      <div class="table-wrap">
        <el-table :data="items" empty-text="还没有会话，先生成一条模拟样本">
          <el-table-column prop="session_uuid" label="会话" min-width="140" />
          <el-table-column prop="task_title" label="任务" min-width="160" />
          <el-table-column prop="device_sn" label="设备" width="120" />
          <el-table-column label="时长" width="110">
            <template #default="{ row }">{{ formatClock(row.duration_seconds) }}</template>
          </el-table-column>
          <el-table-column prop="frame_count" label="帧数" width="80" />
          <el-table-column prop="segment_count" label="切片" width="70" />
          <el-table-column label="审核" width="90">
            <template #default="{ row }">
              <el-tag :type="row.is_reviewed ? 'success' : 'info'" size="small">{{ row.is_reviewed ? '已通过' : '未完成' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="创建时间" min-width="170">
            <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="annotate(row)">去标注</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </section>
  </div>
</template>

<style scoped>
.gap { margin-bottom: 12px; }
.block { padding: 16px; margin-bottom: 16px; }
.block h3 { margin: 0 0 12px; }
.block-head { display: flex; justify-content: space-between; align-items: center; }
.block-head span { color: #909399; }
.upload-icon { font-size: 28px; color: #1890ff; margin-bottom: 6px; }
.progress { margin: 8px 0 12px; }
</style>
