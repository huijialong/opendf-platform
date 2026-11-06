<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ACTION_COLOR, ACTION_LABELS } from '@/utils/dict'
import { formatClock } from '@/utils/format'

const props = defineProps({
  videoUrl: { type: String, default: '' },
  trajectoryData: { type: Array, default: () => [] },
  segments: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:segments'])

const videoRef = ref(null)
const canvasRef = ref(null)
const wrapRef = ref(null)
const mediaDuration = ref(0)
const cursorLeft = ref(0)
const wrapWidth = ref(800)
const clock = ref('00:00.00 / 00:00.00')
const dragBox = ref(null)
const pending = ref(null)
const localSegments = ref([])

const primaryLabels = computed(() => ACTION_LABELS.filter((item) => ['APPROACH', 'GRASP', 'PLACE'].includes(item.value)))
const extraLabels = computed(() => ACTION_LABELS.filter((item) => !['APPROACH', 'GRASP', 'PLACE'].includes(item.value)))

let rafId = 0
let dragging = false
let moved = false
let anchorX = 0
let anchorTime = 0

function currentDuration() {
  if (mediaDuration.value > 0) return mediaDuration.value
  const data = props.trajectoryData || []
  if (!data.length) return 0
  const last = Number(data[data.length - 1].timestamp) || 0
  const step = data.length > 1 ? Number(data[1].timestamp) - Number(data[0].timestamp) : 1 / 30
  return last + Math.max(step, 0)
}

function sameSegments(left, right) {
  return JSON.stringify(left || []) === JSON.stringify(right || [])
}

watch(
  () => props.segments,
  (value) => {
    if (!sameSegments(value, localSegments.value)) {
      localSegments.value = JSON.parse(JSON.stringify(value || []))
      drawWaveform()
    }
  },
  { deep: true, immediate: true },
)

watch(
  () => props.trajectoryData,
  () => drawWaveform(),
)

watch(
  () => props.videoUrl,
  () => {
    mediaDuration.value = 0
  },
)

function onMetaLoaded() {
  const duration = videoRef.value?.duration
  mediaDuration.value = duration && Number.isFinite(duration) ? duration : 0
  drawWaveform()
}

function publish(next) {
  localSegments.value = next
  drawWaveform()
  emit('update:segments', JSON.parse(JSON.stringify(next)))
}

function seekTo(time) {
  const video = videoRef.value
  const duration = currentDuration()
  if (!video || !duration) return
  const next = Math.min(Math.max(time, 0), Math.max(duration - 0.001, 0))
  video.currentTime = next
  cursorLeft.value = (next / duration) * wrapWidth.value
  clock.value = `${formatClock(next)} / ${formatClock(duration)}`
}

function togglePlay() {
  const video = videoRef.value
  if (!video) return
  if (video.paused) video.play()
  else video.pause()
}

function relX(event) {
  const rect = wrapRef.value.getBoundingClientRect()
  return Math.min(Math.max(event.clientX - rect.left, 0), rect.width)
}

function xToTime(x) {
  const duration = currentDuration()
  if (!duration || !wrapWidth.value) return 0
  return (x / wrapWidth.value) * duration
}

function onMouseDown(event) {
  if (!currentDuration()) return
  dragging = true
  moved = false
  anchorX = relX(event)
  anchorTime = xToTime(anchorX)
  dragBox.value = { left: anchorX, width: 0 }
  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('mouseup', onMouseUp)
}

function onMouseMove(event) {
  if (!dragging) return
  const x = relX(event)
  if (Math.abs(x - anchorX) > 4) moved = true
  dragBox.value = { left: Math.min(anchorX, x), width: Math.abs(x - anchorX) }
}

function onMouseUp(event) {
  if (!dragging) return
  dragging = false
  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('mouseup', onMouseUp)
  const x = relX(event)
  const end = xToTime(x)
  dragBox.value = null
  if (!moved || Math.abs(end - anchorTime) <= 0.3) {
    seekTo(xToTime(anchorX))
    pending.value = null
    return
  }
  pending.value = {
    start_time: Math.min(anchorTime, end),
    end_time: Math.max(anchorTime, end),
  }
  drawWaveform()
}

function tag(label) {
  if (!pending.value) return
  publish([
    ...localSegments.value,
    {
      action_label: label,
      start_time: Number(pending.value.start_time.toFixed(3)),
      end_time: Number(pending.value.end_time.toFixed(3)),
      quality_score: 5,
      notes: '',
    },
  ])
  pending.value = null
}

function cancelPending() {
  pending.value = null
  drawWaveform()
}

function removeSegment(index) {
  publish(localSegments.value.filter((_, itemIndex) => itemIndex !== index))
}

function colorOf(label) {
  return ACTION_COLOR[label] || '#64748b'
}

function drawWaveform() {
  const canvas = canvasRef.value
  const wrap = wrapRef.value
  if (!canvas || !wrap) return
  const cssW = wrap.clientWidth || 800
  const cssH = 120
  const dpr = window.devicePixelRatio || 1
  canvas.width = Math.round(cssW * dpr)
  canvas.height = Math.round(cssH * dpr)
  canvas.style.width = `${cssW}px`
  canvas.style.height = `${cssH}px`
  wrapWidth.value = cssW
  const ctx = canvas.getContext('2d')
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  ctx.clearRect(0, 0, cssW, cssH)
  ctx.fillStyle = '#f8fafc'
  ctx.fillRect(0, 0, cssW, cssH)

  ctx.strokeStyle = '#e2e8f0'
  ctx.lineWidth = 1
  ctx.beginPath()
  ctx.moveTo(0, 60)
  ctx.lineTo(cssW, 60)
  ctx.stroke()

  const duration = currentDuration()
  if (duration > 0) {
    ctx.font = '11px sans-serif'
    ctx.fillStyle = '#94a3b8'
    const step = duration > 16 ? 2 : 1
    for (let t = 0; t <= duration + 0.001; t += step) {
      const x = (t / duration) * cssW
      ctx.strokeStyle = '#e2e8f0'
      ctx.beginPath()
      ctx.moveTo(x, 16)
      ctx.lineTo(x, cssH)
      ctx.stroke()
      ctx.fillText(`${Math.round(t)}s`, Math.min(x + 3, cssW - 24), 12)
    }
  }

  const bands = [...localSegments.value]
  if (pending.value) bands.push({ ...pending.value, action_label: 'PENDING' })
  bands.forEach((seg) => {
    if (!duration) return
    const x0 = (seg.start_time / duration) * cssW
    const x1 = (seg.end_time / duration) * cssW
    ctx.fillStyle = seg.action_label === 'PENDING' ? 'rgba(239, 68, 68, 0.16)' : hexAlpha(colorOf(seg.action_label), 0.18)
    ctx.fillRect(x0, 0, Math.max(x1 - x0, 1), cssH)
  })

  const data = props.trajectoryData || []
  if (!data.length || !duration) return

  strokeSeries(ctx, data, duration, cssW, '#f59e0b', 1.5, (pt) => 60 - (Number(pt.velocity) / 0.12) * 46)
  strokeSeries(ctx, data, duration, cssW, '#3b82f6', 2, (pt) => 110 - (Number(pt.gripper_width) / 0.1) * 90)
}

function strokeSeries(ctx, data, duration, cssW, color, width, yOf) {
  ctx.beginPath()
  ctx.strokeStyle = color
  ctx.lineWidth = width
  data.forEach((pt, index) => {
    const x = (Number(pt.timestamp) / duration) * cssW
    const y = Math.min(116, Math.max(18, yOf(pt)))
    if (index === 0) ctx.moveTo(x, y)
    else ctx.lineTo(x, y)
  })
  ctx.stroke()
}

function hexAlpha(hex, alpha) {
  const raw = hex.replace('#', '')
  const value = Number.parseInt(raw, 16)
  const r = (value >> 16) & 255
  const g = (value >> 8) & 255
  const b = value & 255
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

function tick() {
  const video = videoRef.value
  const duration = currentDuration()
  if (video && duration) {
    const time = video.currentTime || 0
    cursorLeft.value = (time / duration) * wrapWidth.value
    clock.value = `${formatClock(time)} / ${formatClock(duration)}`
  }
  rafId = requestAnimationFrame(tick)
}

function onKeydown(event) {
  if (event.target && ['INPUT', 'TEXTAREA'].includes(event.target.tagName)) return
  if (event.code === 'Space') {
    event.preventDefault()
    togglePlay()
  } else if (event.code === 'ArrowRight') {
    seekTo((videoRef.value?.currentTime || 0) + 0.1)
  } else if (event.code === 'ArrowLeft') {
    seekTo((videoRef.value?.currentTime || 0) - 0.1)
  }
}

let observer
onMounted(() => {
  drawWaveform()
  rafId = requestAnimationFrame(tick)
  observer = new ResizeObserver(() => drawWaveform())
  if (wrapRef.value) observer.observe(wrapRef.value)
  window.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  cancelAnimationFrame(rafId)
  observer?.disconnect()
  window.removeEventListener('keydown', onKeydown)
  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('mouseup', onMouseUp)
})

defineExpose({ seekTo, togglePlay })
</script>

<template>
  <div class="timeline-player">
    <div class="video-box">
      <video
        v-if="videoUrl"
        ref="videoRef"
        :src="videoUrl"
        controls
        playsinline
        preload="metadata"
        @loadedmetadata="onMetaLoaded"
      />
      <div v-else class="video-empty">当前会话没有视频，波形仍可按轨迹时间轴标注。</div>
    </div>

    <div class="wave-meta">
      <span><i class="dot grip" />夹爪开合</span>
      <span><i class="dot vel" />末端速度</span>
      <span><i class="dot cursor" />播放游标</span>
      <strong>{{ clock }}</strong>
    </div>

    <div ref="wrapRef" class="canvas-wrap" @mousedown.prevent="onMouseDown">
      <canvas ref="canvasRef" />
      <div class="time-cursor" :style="{ left: cursorLeft + 'px' }">
        <span>{{ clock.split(' / ')[0] }}</span>
      </div>
      <div v-if="dragBox" class="sel-box" :style="{ left: dragBox.left + 'px', width: dragBox.width + 'px' }" />
    </div>
    <p class="hint">点击波形跳转时间；拖拽超过 0.3 秒后选择 Approach / Grasp / Place。空格播放，左右方向键微调。</p>

    <div v-if="pending" class="label-pop">
      <span>{{ pending.start_time.toFixed(2) }}s – {{ pending.end_time.toFixed(2) }}s</span>
      <el-button
        v-for="item in primaryLabels"
        :key="item.value"
        size="small"
        :style="{ background: item.color, borderColor: item.color, color: '#fff' }"
        @click="tag(item.value)"
      >
        {{ item.label }}
      </el-button>
      <el-button v-for="item in extraLabels" :key="item.value" size="small" @click="tag(item.value)">
        {{ item.label }}
      </el-button>
      <el-button size="small" link @click="cancelPending">取消</el-button>
    </div>

    <div class="segment-tags">
      <el-tag
        v-for="(seg, index) in localSegments"
        :key="`${seg.action_label}-${seg.start_time}-${index}`"
        closable
        effect="plain"
        class="seg-tag"
        :style="{ color: colorOf(seg.action_label), borderColor: colorOf(seg.action_label) }"
        @click="seekTo(seg.start_time)"
        @close="removeSegment(index)"
      >
        {{ seg.action_label }} ({{ Number(seg.start_time).toFixed(2) }}s - {{ Number(seg.end_time).toFixed(2) }}s)
      </el-tag>
    </div>
  </div>
</template>

<style scoped>
.timeline-player {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.video-box video,
.video-empty {
  width: 100%;
  max-height: 400px;
  background: #000;
  border-radius: 6px;
}

.video-box video {
  display: block;
  object-fit: contain;
}

.video-empty {
  min-height: 180px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #cbd5e1;
  padding: 24px;
  text-align: center;
}

.wave-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  align-items: center;
  color: #64748b;
  font-size: 12px;
}

.wave-meta strong {
  margin-left: auto;
  color: #0f172a;
  font-variant-numeric: tabular-nums;
}

.dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 6px;
}

.dot.grip { background: #3b82f6; }
.dot.vel { background: #f59e0b; }
.dot.cursor { background: #ef4444; }

.canvas-wrap {
  position: relative;
  width: 100%;
  background: #f8fafc;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  cursor: crosshair;
  user-select: none;
}

.canvas-wrap canvas {
  display: block;
  width: 100%;
  height: 120px;
}

.time-cursor {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background: #ef4444;
  pointer-events: none;
  z-index: 3;
}

.time-cursor span {
  position: absolute;
  top: 2px;
  left: 4px;
  background: #ef4444;
  color: #fff;
  font-size: 10px;
  line-height: 16px;
  padding: 0 4px;
  border-radius: 2px;
  white-space: nowrap;
}

.sel-box {
  position: absolute;
  top: 0;
  bottom: 0;
  background: rgba(239, 68, 68, 0.18);
  border-left: 1px solid #ef4444;
  border-right: 1px solid #ef4444;
  pointer-events: none;
}

.hint {
  margin: 0;
  color: #94a3b8;
  font-size: 12px;
}

.label-pop {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  padding: 10px 12px;
  background: #fff7ed;
  border: 1px solid #fdba74;
  border-radius: 6px;
}

.segment-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.seg-tag {
  cursor: pointer;
}
</style>
