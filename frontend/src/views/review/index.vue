<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getSettings, reviewDecision, reviewQueue } from '@/api/modules'
import { formatClock } from '@/utils/format'

const router = useRouter()
const loading = ref(false)
const error = ref('')
const items = ref([])
const total = ref(0)
const page = ref(1)
const status = ref('PENDING')
const summary = ref({ pending: 0, approved: 0, rejected: 0, pass_rate: 0 })
const qaRatio = ref(20)
const rejectOpen = ref(false)
const acting = ref(false)
const current = ref(null)
const form = reactive({ reason: '' })

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [queue, settings] = await Promise.all([
      reviewQueue({ status: status.value || undefined, page: page.value, page_size: 10 }),
      getSettings(),
    ])
    items.value = queue.data.items
    total.value = queue.data.total
    summary.value = queue.data.summary
    qaRatio.value = settings.data.qa_ratio
  } catch (err) {
    error.value = err?.message || '审核队列加载失败'
  } finally {
    loading.value = false
  }
}

function openAnnotation(row) {
  router.push({ path: '/annotation', query: { session: row.session_id, t: row.start_time } })
}

async function approve(row) {
  acting.value = true
  try {
    await reviewDecision({ segment_id: row.id, decision: 'APPROVED' })
    ElMessage.success('已通过')
    await load()
  } finally {
    acting.value = false
  }
}

function openReject(row) {
  current.value = row
  form.reason = ''
  rejectOpen.value = true
}

async function submitReject() {
  if (!form.reason.trim()) {
    ElMessage.warning('驳回必须写明问题和时间点')
    return
  }
  acting.value = true
  try {
    await reviewDecision({
      segment_id: current.value.id,
      decision: 'REJECTED',
      reason: form.reason.trim(),
    })
    rejectOpen.value = false
    ElMessage.success('已驳回')
    await load()
  } finally {
    acting.value = false
  }
}

onMounted(load)
</script>

<template>
  <div v-loading="loading">
    <div class="page-head">
      <div>
        <h2>审核模块</h2>
        <p>按批次抽检动作切片。驳回时要写清时间点，例如夹爪闭合时机漂移了几帧。</p>
      </div>
    </div>
    <el-alert v-if="error" type="error" :title="error" show-icon class="gap">
      <el-button size="small" @click="load">重试</el-button>
    </el-alert>
    <div class="summary">
      <div class="odf-card stat"><span>待审</span><strong>{{ summary.pending }}</strong></div>
      <div class="odf-card stat"><span>通过</span><strong>{{ summary.approved }}</strong></div>
      <div class="odf-card stat"><span>驳回</span><strong>{{ summary.rejected }}</strong></div>
      <div class="odf-card stat"><span>通过率</span><strong>{{ summary.pass_rate }}%</strong></div>
      <div class="odf-card stat"><span>抽检比例</span><strong>{{ qaRatio }}%</strong></div>
    </div>
    <section class="odf-card block">
      <div class="filter-bar">
        <el-select v-model="status" style="width: 160px" @change="page = 1; load()">
          <el-option label="待审核" value="PENDING" />
          <el-option label="已通过" value="APPROVED" />
          <el-option label="已驳回" value="REJECTED" />
          <el-option label="全部" value="" />
        </el-select>
      </div>
      <div class="table-wrap">
        <el-table :data="items" empty-text="这个状态下没有切片">
          <el-table-column prop="task_code" label="任务" min-width="140" />
          <el-table-column prop="task_title" label="名称" min-width="160" />
          <el-table-column prop="action_label" label="动作" width="120" />
          <el-table-column label="区间" min-width="170">
            <template #default="{ row }">{{ formatClock(row.start_time) }} – {{ formatClock(row.end_time) }}</template>
          </el-table-column>
          <el-table-column prop="quality_score" label="质量" width="70" />
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <el-tag size="small" :type="row.review_status === 'APPROVED' ? 'success' : row.review_status === 'REJECTED' ? 'danger' : 'warning'">
                {{ row.review_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="reject_reason" label="驳回原因" min-width="200" show-overflow-tooltip />
          <el-table-column label="操作" width="210" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openAnnotation(row)">回放</el-button>
              <el-button link type="success" :disabled="acting" @click="approve(row)">通过</el-button>
              <el-button link type="danger" :disabled="acting" @click="openReject(row)">驳回</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <div class="pager">
        <el-pagination
          v-model:current-page="page"
          background
          layout="total, prev, pager, next"
          :total="total"
          :page-size="10"
          @current-change="load"
        />
      </div>
    </section>

    <el-dialog v-model="rejectOpen" title="驳回返工" width="480px">
      <p class="tip">说明要能定位到时间，例如「00:14 夹爪闭合时机标注漂移 3 帧」。</p>
      <el-input v-model="form.reason" type="textarea" :rows="4" maxlength="300" show-word-limit />
      <template #footer>
        <el-button @click="rejectOpen = false">取消</el-button>
        <el-button type="danger" :loading="acting" @click="submitReject">确认驳回</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.gap { margin-bottom: 12px; }
.summary {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
.stat { padding: 14px 16px; }
.stat span { color: #909399; font-size: 13px; }
.stat strong { display: block; margin-top: 4px; font-size: 24px; color: #1f2d3d; }
.block { padding: 16px; }
.tip { margin-top: 0; color: #909399; font-size: 13px; }
@media (max-width: 900px) {
  .summary { grid-template-columns: repeat(2, 1fr); }
}
</style>
