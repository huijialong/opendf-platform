<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { assignTasks, createTask, deleteTask, listTasks, updateTask } from '@/api/modules'
import { PRIORITY, SCENE_OPTIONS, TASK_STATUS, priorityMeta, taskStatus } from '@/utils/dict'
import { formatDate } from '@/utils/format'

const loading = ref(false)
const error = ref('')
const items = ref([])
const total = ref(0)
const page = ref(1)
const selected = ref([])
const dialog = ref(false)
const saving = ref(false)
const assignOpen = ref(false)
const assignee = ref('')

const query = reactive({ keyword: '', status: '', priority: '' })
const form = reactive(blank())

function blank() {
  return {
    id: null,
    title: '',
    scene_category: '机械臂抓取',
    priority: 'MEDIUM',
    status: 'PENDING',
    assignee: '',
    sample_target: 50,
  }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await listTasks({ ...query, page: page.value, page_size: 10 })
    items.value = res.data.items
    total.value = res.data.total
  } catch (err) {
    error.value = err?.message || '任务列表加载失败'
  } finally {
    loading.value = false
  }
}

function openCreate() {
  Object.assign(form, blank())
  dialog.value = true
}

function openEdit(row) {
  Object.assign(form, {
    id: row.id,
    title: row.title,
    scene_category: row.scene_category,
    priority: row.priority,
    status: row.status,
    assignee: row.assignee || '',
    sample_target: row.sample_target,
  })
  dialog.value = true
}

async function submit() {
  if (!form.title.trim()) {
    ElMessage.warning('请填写任务名称')
    return
  }
  saving.value = true
  try {
    const payload = {
      title: form.title.trim(),
      scene_category: form.scene_category,
      priority: form.priority,
      status: form.status,
      assignee: form.assignee || null,
      sample_target: form.sample_target,
    }
    if (form.id) await updateTask(form.id, payload)
    else await createTask(payload)
    dialog.value = false
    ElMessage.success(form.id ? '任务已更新' : '任务已创建')
    await load()
  } finally {
    saving.value = false
  }
}

async function remove(row) {
  await ElMessageBox.confirm(`删除任务「${row.title}」及其会话？`, '删除任务', { type: 'warning' })
  await deleteTask(row.id)
  ElMessage.success('已删除')
  await load()
}

async function submitAssign() {
  if (!assignee.value.trim() || !selected.value.length) {
    ElMessage.warning('选择任务并填写负责人')
    return
  }
  await assignTasks({ assignee: assignee.value.trim(), task_ids: selected.value.map((row) => row.id) })
  assignOpen.value = false
  ElMessage.success('已批量指派')
  await load()
}

function exportReport() {
  const header = ['任务编号', '任务名称', '场景', '负责人', '优先级', '状态', '进度', '目标', '已完成']
  const lines = [header.join(',')]
  items.value.forEach((row) => {
    lines.push([
      row.task_code,
      row.title,
      row.scene_category,
      row.assignee || '',
      priorityMeta(row.priority).label,
      taskStatus(row.status).label,
      `${row.progress}%`,
      row.sample_target,
      row.completed_samples,
    ].join(','))
  })
  const blob = new Blob([`\ufeff${lines.join('\n')}`], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'task-progress.csv'
  link.click()
  URL.revokeObjectURL(url)
}

onMounted(load)
</script>

<template>
  <div v-loading="loading">
    <div class="page-head">
      <div>
        <h2>任务管理</h2>
        <p>按场景把采集批次分给负责人，跟踪待采集、清洗、标注、审核和归档。</p>
      </div>
      <div class="head-actions">
        <el-button @click="exportReport">导出进度报告</el-button>
        <el-button :disabled="!selected.length" @click="assignOpen = true">批量指派</el-button>
        <el-button type="primary" @click="openCreate">新建任务</el-button>
      </div>
    </div>
    <el-alert v-if="error" type="error" :title="error" show-icon class="gap">
      <el-button size="small" @click="load">重试</el-button>
    </el-alert>
    <section class="odf-card block">
      <div class="filter-bar">
        <el-input v-model="query.keyword" placeholder="任务名称 / 编号" clearable style="width: 220px" @keyup.enter="load" />
        <el-select v-model="query.status" placeholder="状态" clearable style="width: 140px">
          <el-option v-for="(meta, key) in TASK_STATUS" :key="key" :label="meta.label" :value="key" />
        </el-select>
        <el-select v-model="query.priority" placeholder="优先级" clearable style="width: 120px">
          <el-option v-for="(meta, key) in PRIORITY" :key="key" :label="meta.label" :value="key" />
        </el-select>
        <el-button type="primary" @click="page = 1; load()">查询</el-button>
      </div>
      <div class="table-wrap">
        <el-table :data="items" @selection-change="selected = $event">
          <el-table-column type="selection" width="46" />
          <el-table-column prop="task_code" label="任务编号" min-width="150" />
          <el-table-column prop="title" label="任务名称" min-width="180" />
          <el-table-column prop="scene_category" label="场景类型" min-width="120" />
          <el-table-column prop="assignee" label="负责人" width="100">
            <template #default="{ row }">{{ row.assignee || '未分配' }}</template>
          </el-table-column>
          <el-table-column label="优先级" width="90">
            <template #default="{ row }">
              <el-tag :type="priorityMeta(row.priority).type" size="small">{{ priorityMeta(row.priority).label }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="taskStatus(row.status).type" size="small">{{ taskStatus(row.status).label }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="进度" min-width="160">
            <template #default="{ row }">
              <el-progress :percentage="row.progress" :stroke-width="8" />
            </template>
          </el-table-column>
          <el-table-column label="创建时间" min-width="170">
            <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
              <el-button link type="danger" @click="remove(row)">删除</el-button>
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

    <el-dialog v-model="dialog" :title="form.id ? '编辑任务' : '新建任务'" width="520px">
      <el-form label-width="96px">
        <el-form-item label="任务名称" required>
          <el-input v-model="form.title" maxlength="128" />
        </el-form-item>
        <el-form-item label="场景类型">
          <el-select v-model="form.scene_category" style="width: 100%">
            <el-option v-for="item in SCENE_OPTIONS" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="form.priority" style="width: 100%">
            <el-option v-for="(meta, key) in PRIORITY" :key="key" :label="meta.label" :value="key" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" style="width: 100%">
            <el-option v-for="(meta, key) in TASK_STATUS" :key="key" :label="meta.label" :value="key" />
          </el-select>
        </el-form-item>
        <el-form-item label="负责人">
          <el-input v-model="form.assignee" placeholder="林可 / 周衡 / 赵敏" />
        </el-form-item>
        <el-form-item label="目标样本">
          <el-input-number v-model="form.sample_target" :min="1" :max="10000" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="assignOpen" title="批量指派" width="420px">
      <el-input v-model="assignee" placeholder="负责人姓名" />
      <template #footer>
        <el-button @click="assignOpen = false">取消</el-button>
        <el-button type="primary" @click="submitAssign">指派 {{ selected.length }} 条</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.gap { margin-bottom: 12px; }
.block { padding: 16px; }
</style>
