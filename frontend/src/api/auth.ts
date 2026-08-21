import http from './http'

export interface UserInfo {
  id: number
  username: string
  display_name: string
  role: string
  status: string
  phone: string
  email: string
  must_change_password: boolean
  last_login_at: string | null
  created_at: string
}

export async function login(username: string, password: string) {
  const { data } = await http.post('/auth/login', { username, password })
  return data as { access_token: string; user: UserInfo; must_change_password: boolean }
}

export async function fetchMe() {
  const { data } = await http.get('/auth/me')
  return data as UserInfo
}

export async function changePassword(old_password: string, new_password: string) {
  await http.post('/auth/change-password', { old_password, new_password })
}
