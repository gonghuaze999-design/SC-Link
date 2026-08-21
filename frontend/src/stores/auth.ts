import { defineStore } from 'pinia'
import { fetchMe, login as apiLogin, type UserInfo } from '../api/auth'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('sclink_token') || '',
    user: null as UserInfo | null,
  }),
  getters: {
    isLoggedIn: (s) => !!s.token,
    isAdmin: (s) => s.user?.role === 'admin',
  },
  actions: {
    async login(username: string, password: string): Promise<boolean> {
      const res = await apiLogin(username, password)
      this.token = res.access_token
      localStorage.setItem('sclink_token', res.access_token)
      this.user = res.user
      return res.must_change_password
    },
    async loadMe() {
      if (!this.token) return
      try {
        this.user = await fetchMe()
      } catch {
        this.logout()
      }
    },
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem('sclink_token')
    },
  },
})
