import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      component: () => import('../views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/change-password',
      component: () => import('../views/ChangePasswordView.vue'),
      meta: { title: '设置密码' },
    },
    {
      path: '/',
      component: () => import('../components/AppLayout.vue'),
      children: [
        { path: '', redirect: '/dashboard' },
        {
          path: 'dashboard',
          component: () => import('../views/DashboardView.vue'),
          meta: { title: '我的工作' },
        },
        {
          path: 'board',
          component: () => import('../views/BoardView.vue'),
          meta: { title: '供需看板' },
        },
        {
          path: 'match',
          component: () => import('../views/MatchView.vue'),
          meta: { title: '匹配中心' },
        },
        {
          path: 'deals',
          component: () => import('../views/DealPlanView.vue'),
          meta: { title: '成本收益' },
        },
        {
          path: 'duty',
          component: () => import('../views/DutyView.vue'),
          meta: { title: '值班机器人' },
        },
        {
          path: 'entities',
          component: () => import('../views/EntitiesView.vue'),
          meta: { title: '主体管理' },
        },
        {
          path: 'orders',
          component: () => import('../views/OrdersView.vue'),
          meta: { title: '订单跟踪' },
        },
        {
          path: 'analytics',
          component: () => import('../views/AnalyticsView.vue'),
          meta: { title: '分析中台' },
        },
        {
          path: 'shares',
          component: () => import('../views/SharesView.vue'),
          meta: { title: '共享管理' },
        },
        {
          path: 'users',
          component: () => import('../views/UsersView.vue'),
          meta: { title: '用户管理', adminOnly: true },
        },
        {
          path: 'audit',
          component: () => import('../views/AuditView.vue'),
          meta: { title: '审计日志', adminOnly: true },
        },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!auth.isLoggedIn && !to.meta.public) return '/login'
  if (to.meta.public && auth.isLoggedIn) return '/dashboard'
  if (to.meta.adminOnly && !auth.isAdmin) return '/dashboard'
  // 初设/重置密码后强制先改密
  if (auth.isLoggedIn && auth.user?.must_change_password && to.path !== '/change-password') return '/change-password'
  if (auth.isLoggedIn && !auth.user?.must_change_password && to.path === '/change-password') return '/dashboard'
  return true
})

export default router
