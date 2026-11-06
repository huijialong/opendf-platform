<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTagsStore } from '@/stores/tags'

const route = useRoute()
const router = useRouter()
const tags = useTagsStore()
const scrollRef = ref(null)
const menu = ref({ visible: false, x: 0, y: 0, path: '' })

function onWheel(event) {
  if (!scrollRef.value) return
  scrollRef.value.scrollLeft += event.deltaY
}

function close(event, path) {
  event.preventDefault()
  event.stopPropagation()
  const result = tags.close(path)
  if (!result) return
  if (route.path === path && result.fallback) router.push(result.fallback.fullPath)
}

function onContext(event, path) {
  menu.value = { visible: true, x: event.clientX, y: event.clientY, path }
}

function closeOthers() {
  tags.closeOthers(menu.value.path)
  menu.value.visible = false
  if (route.path !== menu.value.path) {
    const target = tags.visited.find((item) => item.path === menu.value.path)
    if (target) router.push(target.fullPath)
  }
}
</script>

<template>
  <div class="tags-view" @click="menu.visible = false">
    <div ref="scrollRef" class="tags-scroll" @wheel.prevent="onWheel">
      <router-link
        v-for="tag in tags.visited"
        :key="tag.path"
        :to="tag.fullPath"
        class="tag-item"
        :class="{ active: tag.path === route.path }"
        @contextmenu.prevent="onContext($event, tag.path)"
      >
        {{ tag.title }}
        <el-icon v-if="!tag.affix" @click="close($event, tag.path)"><Close /></el-icon>
      </router-link>
    </div>
    <ul v-if="menu.visible" class="tag-menu" :style="{ left: menu.x + 'px', top: menu.y + 'px' }">
      <li @click="closeOthers">关闭其他</li>
    </ul>
  </div>
</template>

<style scoped>
.tag-menu {
  position: fixed;
  z-index: 20;
  margin: 0;
  padding: 4px 0;
  list-style: none;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12);
  min-width: 120px;
}

.tag-menu li {
  padding: 6px 12px;
  font-size: 13px;
  cursor: pointer;
}

.tag-menu li:hover {
  background: #f5f7fa;
}
</style>
