export const TASK_STATUS = {
  PENDING: { label: '待采集', type: 'info' },
  COLLECTING: { label: '采集中', type: 'primary' },
  CLEANING: { label: '待清洗', type: 'warning' },
  ANNOTATING: { label: '标注中', type: 'primary' },
  REVIEWING: { label: '待审核', type: 'warning' },
  DONE: { label: '已归档', type: 'success' },
}

export const PRIORITY = {
  LOW: { label: '低', type: 'info' },
  MEDIUM: { label: '中', type: 'primary' },
  HIGH: { label: '高', type: 'warning' },
  URGENT: { label: '紧急', type: 'danger' },
}

export const DEVICE_STATUS = {
  ONLINE: { label: '在线', type: 'success' },
  OFFLINE: { label: '离线', type: 'info' },
  CALIBRATING: { label: '标定中', type: 'warning' },
}

export const DEVICE_TYPES = [
  { value: 'UMI_GRIPPER', label: 'Stanford UMI 手持夹爪' },
  { value: 'PICO_VR', label: 'Pico VR 4 / Neo 3' },
  { value: 'EGO_CAM', label: 'GoPro / 第一视角相机' },
  { value: 'ROBOT_ARM', label: 'Piper / Franka 机械臂' },
]

export const DEVICE_TYPE_LABEL = Object.fromEntries(DEVICE_TYPES.map((item) => [item.value, item.label]))

export const SCENE_OPTIONS = ['机械臂抓取', 'VR第一视角', '触觉作业', '工业巡检', '抓取摆放', '双手装配', '避障导航']

export const ACTION_LABELS = [
  { value: 'APPROACH', label: 'Approach', hint: '接近', color: '#3b82f6' },
  { value: 'GRASP', label: 'Grasp', hint: '抓取', color: '#16a34a' },
  { value: 'PLACE', label: 'Place', hint: '放置', color: '#9333ea' },
  { value: 'LIFT', label: 'Lift', hint: '提起', color: '#d97706' },
  { value: 'MOVE', label: 'Move', hint: '搬运', color: '#0f766e' },
]

export const ACTION_COLOR = Object.fromEntries(ACTION_LABELS.map((item) => [item.value, item.color]))

export function taskStatus(value) {
  return TASK_STATUS[value] || { label: value || '—', type: 'info' }
}

export function priorityMeta(value) {
  return PRIORITY[value] || { label: value || '—', type: 'info' }
}

export function deviceStatus(value) {
  return DEVICE_STATUS[value] || { label: value || '—', type: 'info' }
}
