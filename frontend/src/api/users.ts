import http from './http'
import type { UserInfo } from './auth'

export async function fetchInitialPassword() {
  const { data } = await http.get('/users/initial-password')
  return (data as { initial_password: string }).initial_password
}

export async function listUsers(keyword = '') {
  const { data } = await http.get('/users', { params: { keyword } })
  return data as UserInfo[]
}

export async function createUser(payload: {
  username: string
  display_name: string
  role: string
  password?: string
  phone: string
  email: string
}) {
  const { data } = await http.post('/users', payload)
  return data as UserInfo
}

export async function updateUser(
  id: number,
  payload: Partial<{
    display_name: string
    role: string
    status: string
    phone: string
    email: string
    reset_password: boolean
  }>,
) {
  const { data } = await http.patch(`/users/${id}`, payload)
  return data as UserInfo
}
