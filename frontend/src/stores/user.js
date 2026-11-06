import { defineStore } from 'pinia'
import { ref } from 'vue'

const STORAGE_KEY = 'odf-user'
const DEFAULT_USER = {
  username: 'admin',
  name: '系统管理员',
  role: '超级管理员',
  token: 'opendf-admin',
}

function load() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null') || DEFAULT_USER
  } catch {
    return DEFAULT_USER
  }
}

export const useUserStore = defineStore('user', () => {
  const profile = ref(load())

  function setUser(user, token) {
    profile.value = {
      username: user.username,
      name: user.name,
      role: user.role,
      token: token || `opendf-${user.username}`,
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(profile.value))
  }

  function logout() {
    profile.value = { username: '', name: '未登录', role: '', token: '' }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(profile.value))
  }

  return { profile, setUser, logout }
})
