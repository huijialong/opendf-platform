import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useTagsStore = defineStore('tags', () => {
  const visited = ref([{ path: '/dashboard', fullPath: '/dashboard', title: '首页', affix: true }])

  function add(route) {
    if (!route.meta?.title || route.meta.public) return
    const found = visited.value.find((item) => item.path === route.path)
    if (found) {
      found.fullPath = route.fullPath
      found.title = route.meta.title
      return
    }
    visited.value.push({
      path: route.path,
      fullPath: route.fullPath,
      title: route.meta.title,
      affix: !!route.meta.affix,
    })
  }

  function close(path) {
    const index = visited.value.findIndex((item) => item.path === path)
    if (index < 0 || visited.value[index].affix) return null
    const [removed] = visited.value.splice(index, 1)
    const fallback = visited.value[index - 1] || visited.value[index] || visited.value[0]
    return { removed, fallback }
  }

  function closeOthers(path) {
    visited.value = visited.value.filter((item) => item.affix || item.path === path)
  }

  return { visited, add, close, closeOthers }
})
