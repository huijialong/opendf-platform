export function formatBytes(bytes) {
  const value = Number(bytes) || 0
  if (value < 1024) return `${value} B`
  const units = ['KB', 'MB', 'GB', 'TB']
  let size = value / 1024
  let index = 0
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024
    index += 1
  }
  return `${size.toFixed(size >= 10 ? 0 : 1)} ${units[index]}`
}

export function formatClock(seconds) {
  const value = Math.max(0, Number(seconds) || 0)
  const minutes = Math.floor(value / 60)
  const remain = value - minutes * 60
  return `${String(minutes).padStart(2, '0')}:${remain.toFixed(2).padStart(5, '0')}`
}

export function formatDate(value) {
  if (!value) return '—'
  return String(value).replace('T', ' ').replace('Z', '')
}
