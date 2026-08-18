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
      path: '/',
      component: () => import('../components/AppLayout.vue'),
      children: [
        { path: '', redirect: '/dashboard' },
        {
          path: 'dashboard',
          component: () => import('../views/DashboardView.vue'),
          meta: { title: '工作台' },
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
  return true
})

export default router
