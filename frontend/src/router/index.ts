
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/welcome'
  },
  {
    path: '/welcome',
    name: 'Welcome',
    component: () => import('@/views/WelcomePage.vue')
  },
  // 入口按钮中跳转的目标
  {
    path: '/agent',
    name: 'Agent',
    component: () => import('@/views/AgentView.vue').catch(() => import('@/views/WelcomePage.vue'))
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

export default router
