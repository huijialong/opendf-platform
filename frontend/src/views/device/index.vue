<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createDevice, deleteDevice, listDevices, updateDevice } from '@/api/modules'
import { DEVICE_STATUS, DEVICE_TYPES, DEVICE_TYPE_LABEL, deviceStatus } from '@/utils/dict'
import { formatDate } from '@/utils/format'

const loading = ref(false)
const error = ref('')
const items = ref([])
const total = ref(0)
const dialog = ref(false)
const saving = ref(false)
const query = reactive({ keyword: '', device_type: '', status: '' })
const form = reactive(blank())

function blank() {
  return {
    id: null,
    device_sn: '',
    device_type: 'UMI_GRIPPER',
    name: '',
    status: 'ONLINE',
    ip: '',
    mac: '',
    firmware: '',
    calibration: '',
  }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await listDevices({ ...query, page: 1, page_size: 100 })
    items.value = res.data.items
    total.value = res.data.total
  } catch (err) {
    error.value = err?.message || '设备列表加载失败'
  } finally {
    loading.value = false
  }
}

function openCreate() {
  Object.assign(form, blank())
  dialog.value = true
}

function openEdit(row) {
  const meta = row.meta_json || {}
  Object.assign(form, {
    id: row.id,
    device_sn: row.device_sn,
    device_type: row.device_type,
    name: row.name,
    status: row.status,
    ip: meta.ip || '',
    mac: meta.mac || '',
    firmware: meta.firmware || '',
    calibration: meta.intrinsics ? JSON.stringify(meta.intrinsics, null, 2) : '',
  })
  dialog.value = true
}

function buildMeta() {
  let intrinsics = null
  if (form.calibration.trim()) {
    intrinsics = JSON.parse(form.calibration)
  }
  return {
    ip: form.ip,
    mac: form.mac,
    firmware: form.firmware,
    intrinsics,
  }
}

async function submit() {
  if (!form.device_sn.trim() || !form.name.trim()) {
    ElMessage.warning('请填写序列号和名称')
    return
  }
  let meta
  try {
    meta = buildMeta()
  } catch {
    ElMessage.error('标定参数不是合法 JSON')
    return
  }
  saving.value = true
  try {
    const payload = {
      device_sn: form.device_sn.trim(),
      device_type: form.device_type,
      name: form.name.trim(),
      status: form.status,
      meta_json: meta,
    }
    if (form.id) {
      await updateDevice(form.id, {
        device_type: payload.device_type,
        name: payload.name,
        status: payload.status,
        meta_json: meta,
      })
    } else {
      await createDevice(payload)
    }
    dialog.value = false
    ElMessage.success('设备已保存')
    await load()
  } finally {
    saving.value = false
  }
}

async function remove(row) {
  await ElMessageBox.confirm(`移除设备 ${row.device_sn}？`, '删除设备', { type: 'warning' })
  await deleteDevice(row.id)
  ElMessage.success('已删除')
  await load()
}

onMounted(load)
</script>

<template>
  <div v-loading="loading">
    <div class="page-head">
      <div>
        <h2>设备登记</h2>
        <p>登记 Stanford UMI 夹爪、Pico 头显、第一视角相机和机械臂本体，标定参数随设备保存。</p>
      </div>
      <div class="head-actions">
        <el-button type="primary" @click="openCreate">登记设备</el-button>
      </div>
    </div>
    <el-alert v-if="error" type="error" :title="error" show-icon class="gap">
      <el-button size="small" @click="load">重试</el-button>
    </el-alert>
    <section class="odf-card block">
      <div class="filter-bar">
        <el-input v-model="query.keyword" placeholder="名称 / 序列号" clearable style="width: 220px" @keyup.enter="load" />
        <el-select v-model="query.device_type" placeholder="硬件类型" clearable style="width: 220px">
          <el-option v-for="item in DEVICE_TYPES" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select v-model="query.status" placeholder="状态" clearable style="width: 140px">
          <el-option v-for="(meta, key) in DEVICE_STATUS" :key="key" :label="meta.label" :value="key" />
        </el-select>
        <el-button type="primary" @click="load">查询</el-button>
        <span class="count">本机 {{ total }} 台</span>
      </div>
      <div class="table-wrap">
        <el-table :data="items" empty-text="还没有登记设备">
          <el-table-column prop="device_sn" label="序列号" min-width="120" />
          <el-table-column prop="name" label="名称" min-width="200" />
          <el-table-column label="类型" min-width="180">
            <template #default="{ row }">{{ DEVICE_TYPE_LABEL[row.device_type] || row.device_type }}</template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="deviceStatus(row.status).type" size="small">{{ deviceStatus(row.status).label }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="地址" min-width="150">
            <template #default="{ row }">{{ row.meta_json?.ip || '—' }}</template>
          </el-table-column>
          <el-table-column label="固件" min-width="120">
            <template #default="{ row }">{{ row.meta_json?.firmware || '—' }}</template>
          </el-table-column>
          <el-table-column label="登记时间" min-width="170">
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
    </section>

    <el-dialog v-model="dialog" :title="form.id ? '编辑设备' : '登记设备'" width="560px">
      <el-form label-width="96px">
        <el-form-item label="序列号" required>
          <el-input v-model="form.device_sn" :disabled="!!form.id" placeholder="UMI-014" />
        </el-form-item>
        <el-form-item label="硬件类型">
          <el-select v-model="form.device_type" style="width: 100%">
            <el-option v-for="item in DEVICE_TYPES" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="名称" required>
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" style="width: 100%">
            <el-option v-for="(meta, key) in DEVICE_STATUS" :key="key" :label="meta.label" :value="key" />
          </el-select>
        </el-form-item>
        <el-form-item label="IP"><el-input v-model="form.ip" placeholder="192.168.10.21" /></el-form-item>
        <el-form-item label="MAC"><el-input v-model="form.mac" /></el-form-item>
        <el-form-item label="固件"><el-input v-model="form.firmware" /></el-form-item>
        <el-form-item label="标定 JSON">
          <el-input v-model="form.calibration" type="textarea" :rows="4" placeholder='{"fx":615.2,"fy":614.8,"cx":320,"cy":240}' />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.gap { margin-bottom: 12px; }
.block { padding: 16px; }
.count { color: #909399; font-size: 13px; align-self: center; }
</style>
