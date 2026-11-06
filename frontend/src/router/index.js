import { createRouter, createWebHistory } from 'vue-router'
import Layout from '@/layout/index.vue'
import { useTagsStore } from '@/stores/tags'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/index.vue'),
    meta: { public: true, title: '登录' },
  },
  {
    path: '/',
    component: Layout,
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/index.vue'),
        meta: { title: '首页', affix: true },
      },
      {
        path: 'task',
        name: 'Task',
        component: () => import('@/views/task/index.vue'),
        meta: { title: '任务管理' },
      },
      {
        path: 'device',
        name: 'Device',
        component: () => import('@/views/device/index.vue'),
        meta: { title: '设备登记', group: '采集模块' },
      },
      {
        path: 'capture',
        name: 'Capture',
        component: () => import('@/views/capture/index.vue'),
        meta: { title: '采集会话', group: '采集模块' },
      },
      {
        path: 'annotation',
        name: 'Annotation',
        component: () => import('@/views/annotation/index.vue'),
        meta: { title: '标注模块' },
      },
      {
        path: 'review',
        name: 'Review',
        component: () => import('@/views/review/index.vue'),
        meta: { title: '审核模块' },
      },
      {
        path: 'dataset',
        name: 'Dataset',
        component: () => import('@/views/dataset/index.vue'),
        meta: { title: '数据模块' },
      },
      {
        path: 'config',
        name: 'Config',
        component: () => import('@/views/config/index.vue'),
        meta: { title: '配置管理' },
      },
      {
        path: 'system',
        name: 'System',
        component: () => import('@/views/system/index.vue'),
        meta: { title: '系统管理' },
      },
      {
        path: 'docs',
        name: 'Docs',
        component: () => import('@/views/docs/index.vue'),
        meta: { title: '操作手册' },
      },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.afterEach((to) => {
  useTagsStore().add(to)
})

export default router
