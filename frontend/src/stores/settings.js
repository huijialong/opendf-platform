import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

const STORAGE_KEY = 'odf-settings'

function load() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}')
  } catch {
    return {}
  }
}

export const useSettingsStore = defineStore('settings', () => {
  const saved = load()
  const sidebarCollapsed = ref(!!saved.sidebarCollapsed)
  const mobileOpen = ref(false)
  const darkMode = ref(!!saved.darkMode)
  const themeColor = ref(saved.themeColor || '#1890ff')
  const fontSize = ref(saved.fontSize || 'default')
  const fixedHeader = ref(saved.fixedHeader !== false)
  const showTagsView = ref(saved.showTagsView !== false)

  function apply() {
    const root = document.documentElement
    root.classList.toggle('dark', darkMode.value)
    root.style.setProperty('--el-color-primary', themeColor.value)
    root.style.setProperty('--odf-primary', themeColor.value)
    root.setAttribute('data-font-size', fontSize.value)
  }

  function persist() {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        sidebarCollapsed: sidebarCollapsed.value,
        darkMode: darkMode.value,
        themeColor: themeColor.value,
        fontSize: fontSize.value,
        fixedHeader: fixedHeader.value,
        showTagsView: showTagsView.value,
      }),
    )
  }

  watch([sidebarCollapsed, darkMode, themeColor, fontSize, fixedHeader, showTagsView], () => {
    apply()
    persist()
  })

  function toggleSidebar() {
    if (window.innerWidth <= 992) mobileOpen.value = !mobileOpen.value
    else sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function reset() {
    sidebarCollapsed.value = false
    darkMode.value = false
    themeColor.value = '#1890ff'
    fontSize.value = 'default'
    fixedHeader.value = true
    showTagsView.value = true
  }

  return {
    sidebarCollapsed,
    mobileOpen,
    darkMode,
    themeColor,
    fontSize,
    fixedHeader,
    showTagsView,
    apply,
    toggleSidebar,
    reset,
  }
})
