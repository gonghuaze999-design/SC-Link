import http from './http'
import type { UserInfo } from './auth'

export async function listUsers(keyword = '') {
  const { data } = await http.get('/users', { params: { keyword } })
  return data as UserInfo[]
}

export async function createUser(payload: {
  username: string
  display_name: string
  role: string
  password: string
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
    new_password: string
  }>,
) {
  const { data } = await http.patch(`/users/${id}`, payload)
  return data as UserInfo
}
