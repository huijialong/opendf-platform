import request from './request'

export const getStats = () => request.get('/dashboard/stats')

export const listDevices = (params) => request.get('/devices', { params })
export const createDevice = (data) => request.post('/devices', data)
export const updateDevice = (id, data) => request.put(`/devices/${id}`, data)
export const deleteDevice = (id) => request.delete(`/devices/${id}`)

export const listTasks = (params) => request.get('/tasks', { params })
export const createTask = (data) => request.post('/tasks', data)
export const updateTask = (id, data) => request.put(`/tasks/${id}`, data)
export const deleteTask = (id) => request.delete(`/tasks/${id}`)
export const assignTasks = (data) => request.post('/tasks/assign', data)

export const listSessions = (params) => request.get('/sessions', { params })
export const uploadSession = (formData, onProgress) =>
  request.post('/sessions/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: onProgress,
  })
export const createMockSample = (data = {}) => request.post('/sessions/mock-sample', data)

export const getAnnotation = (sessionId) => request.get(`/annotation/session/${sessionId}`)
export const saveSegments = (data) => request.post('/annotation/segments', data)

export const reviewQueue = (params) => request.get('/review/queue', { params })
export const reviewDecision = (data) => request.post('/review/decision', data)

export const exportDataset = (data) => request.post('/datasets/export', data)
export const listExports = () => request.get('/datasets/exports')

export const getSettings = () => request.get('/system/settings')
export const saveSettings = (data) => request.put('/system/settings', data)

export const login = (data) => request.post('/auth/login', data)
export const listUsers = () => request.get('/auth/users')
