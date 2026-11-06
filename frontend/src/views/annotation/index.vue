<script setup>
import { nextTick, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import TimelinePlayer from '@/components/TimelinePlayer/index.vue'
import { createMockSample, getAnnotation, listSessions, saveSegments } from '@/api/modules'
import { ACTION_COLOR } from '@/utils/dict'
import { formatClock } from '@/utils/format'

const route = useRoute()
const playerRef = ref(null)
const loading = ref(false)
const saving = ref(false)
const mocking = ref(false)
const error = ref('')
const sessions = ref([])
const sessionId = ref(null)
const videoUrl = ref('')
const trajectory = ref([])
const segments = ref([])
const sessionMeta = ref(null)
let saveTicket = 0

function optionLabel(row) {
  return `${row.task_title || '未关联任务'} · ${row.session_uuid}`
}

async function loadSessions() {
  const res = await listSessions({ page: 1, page_size: 100 })
  sessions.value = res.data.items
}

async function loadSession(id) {
  if (!id) return
  loading.value = true
  error.value = ''
  try {
    const res = await getAnnotation(id)
    sessionMeta.value = res.data.session
    videoUrl.value = res.data.video_url || ''
    trajectory.value = res.data.trajectory || []
    segments.value = res.data.segments || []
    const jump = Number(route.query.t)
    if (route.query.session && Number(route.query.session) === Number(id) && Number.isFinite(jump)) {
      await nextTick()
      playerRef.value?.seekTo(jump)
    }
  } catch (err) {
    error.value = err?.message || '标注数据加载失败'
  } finally {
    loading.value = false
  }
}

async function persist(nextSegments = segments.value, quiet = false) {
  if (!sessionId.value) return
  const ticket = ++saveTicket
  saving.value = true
  try {
    const res = await saveSegments({
      session_id: sessionId.value,
      segments: nextSegments.map((seg) => ({
        action_label: seg.action_label,
        start_time: Number(seg.start_time),
        end_time: Number(seg.end_time),
        quality_score: Number(seg.quality_score || 5),
        notes: seg.notes || '',
      })),
    })
    if (ticket !== saveTicket) return
    segments.value = res.data
    if (!quiet) ElMessage.success('标注已保存')
  } catch {
    return
  } finally {
    if (ticket === saveTicket) saving.value = false
  }
}

async function onSegments(next) {
  segments.value = next
  await persist(next, true)
  ElMessage.success('区间已写入')
}

function removeAt(index) {
  const next = segments.value.filter((_, itemIndex) => itemIndex !== index)
  segments.value = next
  persist(next, true)
}

async function makeSample() {
  mocking.value = true
  try {
    const res = await createMockSample({})
    await loadSessions()
    sessionId.value = res.data.id
    await loadSession(res.data.id)
    ElMessage.success('模拟样本已生成')
  } finally {
    mocking.value = false
  }
}

onMounted(async () => {
  loading.value = true
  try {
    await loadSessions()
    const wanted = Number(route.query.session)
    const found = sessions.value.find((item) => item.id === wanted)
    sessionId.value = found?.id || sessions.value[0]?.id || null
    if (sessionId.value) await loadSession(sessionId.value)
  } catch (err) {
    error.value = err?.message || '会话加载失败'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div v-loading="loading">
    <div class="page-head">
      <div>
        <h2>多模态标注工作台</h2>
        <p>上方播放第一视角，下方波形同时画出末端速度和夹爪开合。拖拽一段区间，打上 Approach、Grasp 或 Place。</p>
      </div>
      <div class="head-actions">
        <el-select
          v-model="sessionId"
          filterable
          placeholder="选择会话"
          style="width: min(360px, 100%)"
          :disabled="!sessions.length"
          @change="loadSession"
        >
          <el-option v-for="item in sessions" :key="item.id" :label="optionLabel(item)" :value="item.id" />
        </el-select>
        <el-button type="primary" :disabled="!sessionId" :loading="saving" @click="persist()">保存标注</el-button>
      </div>
    </div>

    <el-alert v-if="error" type="error" :title="error" show-icon class="gap">
      <el-button size="small" @click="sessionId ? loadSession(sessionId) : loadSessions()">重试</el-button>
    </el-alert>

    <section v-if="!loading && !sessions.length" class="odf-card empty">
      <el-empty description="还没有可标注的会话">
        <el-button type="primary" :loading="mocking" @click="makeSample">生成模拟样本</el-button>
      </el-empty>
    </section>

    <template v-else-if="sessionId">
      <section class="odf-card player-card">
        <div v-if="sessionMeta" class="meta-line">
          <span>{{ sessionMeta.task_title }}</span>
          <span>{{ sessionMeta.device_sn || '未绑定设备' }}</span>
          <span>{{ formatClock(sessionMeta.duration_seconds) }} · {{ sessionMeta.frame_count }} 帧</span>
        </div>
        <TimelinePlayer
          ref="playerRef"
          :video-url="videoUrl"
          :trajectory-data="trajectory"
          :segments="segments"
          @update:segments="onSegments"
        />
      </section>

      <section class="odf-card block">
        <h3>动作切片</h3>
        <div class="table-wrap">
          <el-table :data="segments" empty-text="在波形上拖拽区间，然后选择 Approach / Grasp / Place">
            <el-table-column label="动作" width="140">
              <template #default="{ row }">
                <strong :style="{ color: ACTION_COLOR[row.action_label] }">{{ row.action_label }}</strong>
              </template>
            </el-table-column>
            <el-table-column label="时间" min-width="180">
              <template #default="{ row }">{{ formatClock(row.start_time) }} – {{ formatClock(row.end_time) }}</template>
            </el-table-column>
            <el-table-column label="帧" width="120">
              <template #default="{ row }">{{ row.start_frame }} – {{ row.end_frame }}</template>
            </el-table-column>
            <el-table-column label="质量" width="140">
              <template #default="{ row }">
                <el-input-number v-model="row.quality_score" :min="1" :max="5" size="small" />
              </template>
            </el-table-column>
            <el-table-column label="备注" min-width="180">
              <template #default="{ row }">
                <el-input v-model="row.notes" size="small" placeholder="可选" />
              </template>
            </el-table-column>
            <el-table-column label="审核" width="110">
              <template #default="{ row }">
                <el-tag size="small" :type="row.review_status === 'APPROVED' ? 'success' : row.review_status === 'REJECTED' ? 'danger' : 'info'">
                  {{ row.review_status || 'PENDING' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="90">
              <template #default="{ $index }">
                <el-button link type="danger" @click="removeAt($index)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.gap { margin-bottom: 12px; }
.player-card, .block, .empty { padding: 16px; }
.block { margin-top: 16px; }
.block h3, .meta-line { margin-top: 0; }
.meta-line {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 12px;
  color: #606266;
  font-size: 13px;
}
</style>
