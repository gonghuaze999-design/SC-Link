import http from './http'

export interface AuditLogItem {
  id: number
  username: string
  action: string
  entity_type: string
  entity_id: string
  detail: string
  old_value: Record<string, unknown> | null
  new_value: Record<string, unknown> | null
  ip: string
  created_at: string
}

export interface LoginLogItem {
  id: number
  username: string
  result: string
  detail: string
  ip: string
  created_at: string
}

export async function listAuditLogs(params: {
  keyword?: string
  action?: string
  limit?: number
}) {
  const { data } = await http.get('/audit-logs', { params })
  return data as AuditLogItem[]
}

export async function listLoginLogs(params: { limit?: number }) {
  const { data } = await http.get('/audit-logs/login', { params })
  return data as LoginLogItem[]
}
