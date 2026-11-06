<script setup>
import { watch } from 'vue'
import { useRoute } from 'vue-router'
import Sidebar from './Sidebar.vue'
import Navbar from './Navbar.vue'
import TagsView from './TagsView.vue'
import RightPanel from '@/components/RightPanel/index.vue'
import { useSettingsStore } from '@/stores/settings'

const settings = useSettingsStore()
const route = useRoute()

watch(
  () => route.path,
  () => {
    settings.mobileOpen = false
  },
)
</script>

<template>
  <div
    class="app-wrapper"
    :class="{
      collapse: settings.sidebarCollapsed,
      'mobile-open': settings.mobileOpen,
    }"
  >
    <Sidebar />
    <div v-if="settings.mobileOpen" class="drawer-mask" @click="settings.mobileOpen = false" />
    <div class="main-container">
      <div class="header-bar" :class="{ fixed: settings.fixedHeader }">
        <Navbar />
        <TagsView v-if="settings.showTagsView" />
      </div>
      <section class="app-main">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </section>
    </div>
    <RightPanel />
  </div>
</template>
