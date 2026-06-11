import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', name: 'Dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '发电监控看板' } },
  { path: '/storage', name: 'Storage', component: () => import('../views/Storage.vue'), meta: { title: '储能管理' } },
  { path: '/alerts', name: 'Alerts', component: () => import('../views/Alerts.vue'), meta: { title: '告警中心' } },
  { path: '/inverters', name: 'Inverters', component: () => import('../views/Inverters.vue'), meta: { title: '逆变器管理' } },
  { path: '/generation', name: 'Generation', component: () => import('../views/Generation.vue'), meta: { title: '发电数据' } },
  { path: '/revenue', name: 'Revenue', component: () => import('../views/Revenue.vue'), meta: { title: '收益明细' } },
  { path: '/payback', name: 'Payback', component: () => import('../views/Payback.vue'), meta: { title: '回本预测' } },
  { path: '/statistics', name: 'Statistics', component: () => import('../views/Statistics.vue'), meta: { title: '统计分析' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  document.title = `${to.meta.title || '光伏监测'} - 家庭光伏发电监测平台`
  next()
})

export default router
