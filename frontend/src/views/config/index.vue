<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getSettings, saveSettings } from '@/api/modules'
import { ACTION_LABELS } from '@/utils/dict'

const loading = ref(false)
const saving = ref(false)
const error = ref('')
const paths = reactive({ storage_raw: '', storage_export: '', raw_files: 0, export_files: 0 })
const form = reactive({
  qa_ratio: 20,
  sample_fps: 30,
  action_labels: ['APPROACH', 'GRASP', 'LIFT', 'MOVE', 'PLACE'],
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await getSettings()
    form.qa_ratio = res.data.qa_ratio
    form.sample_fps = res.data.sample_fps
    form.action_labels = res.data.action_labels || []
    paths.storage_raw = res.data.storage_raw
    paths.storage_export = res.data.storage_export
    paths.raw_files = res.data.raw_files
    paths.export_files = res.data.export_files
  } catch (err) {
    error.value = err?.message || '配置加载失败'
  } finally {
    loading.value = false
  }
}

async function submit() {
  saving.value = true
  try {
    await saveSettings({
      qa_ratio: form.qa_ratio,
      sample_fps: form.sample_fps,
      action_labels: form.action_labels,
    })
    ElMessage.success('配置已保存')
    await load()
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div v-loading="loading">
    <div class="page-head">
      <div>
        <h2>配置管理</h2>
        <p>抽检比例、采样率和动作字典。存储目录由本地引擎固定，不需要另外部署对象存储。</p>
      </div>
    </div>
    <el-alert v-if="error" type="error" :title="error" show-icon class="gap">
      <el-button size="small" @click="load">重试</el-button>
    </el-alert>
    <section class="odf-card block">
      <el-form label-width="120px">
        <el-form-item label="抽检比例">
          <el-radio-group v-model="form.qa_ratio">
            <el-radio-button :value="10">10%</el-radio-button>
            <el-radio-button :value="20">20%</el-radio-button>
            <el-radio-button :value="50">50%</el-radio-button>
            <el-radio-button :value="100">100% 全检</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="采样率">
          <el-input-number v-model="form.sample_fps" :min="1" :max="120" />
          <span class="unit">Hz</span>
        </el-form-item>
        <el-form-item label="动作字典">
          <el-checkbox-group v-model="form.action_labels">
            <el-checkbox v-for="item in ACTION_LABELS" :key="item.value" :value="item.value">
              {{ item.label }} {{ item.hint }}
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="原始目录"><el-input :model-value="`${paths.storage_raw}（${paths.raw_files} 个文件）`" disabled /></el-form-item>
        <el-form-item label="导出目录"><el-input :model-value="`${paths.storage_export}（${paths.export_files} 个包）`" disabled /></el-form-item>
        <el-button type="primary" :loading="saving" @click="submit">保存配置</el-button>
      </el-form>
    </section>
  </div>
</template>

<style scoped>
.gap { margin-bottom: 12px; }
.block { padding: 16px; }
.unit { margin-left: 8px; color: #909399; }
</style>
