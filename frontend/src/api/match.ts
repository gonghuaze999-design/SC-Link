import http from './http'

// ---------- 供需看板 ----------
export interface Publication {
  id: number
  user_id: number
  type: string
  product_line_id: number | null
  title: string
  quantity: string
  price_min: number | null
  price_max: number | null
  currency: string
  validity_until: string | null
  visibility: string
  status: string
  content: string
  intent_modes: string[] | null
  goods_preference: string
  created_at: string
}

export async function listPublications(params: { type?: string; status?: string } = {}) {
  const { data } = await http.get('/publications', { params })
  return data as Publication[]
}
export async function createPublication(payload: Partial<Publication>) {
  const { data } = await http.post('/publications', payload)
  return data as Publication
}
export async function updatePublication(id: number, payload: Partial<Publication>) {
  const { data } = await http.patch(`/publications/${id}`, payload)
  return data as Publication
}
export async function deletePublication(id: number) {
  await http.delete(`/publications/${id}`)
}
export async function parsePublication(text: string) {
  const { data } = await http.post('/publications/parse', { text })
  return data as Partial<Publication> & { product_name?: string }
}

// ---------- 匹配 ----------
export interface MatchEntity {
  id: number
  name: string
  short_name: string
  goods_type: string
  price: number | null
  currency: string
  procurement_modes: string[] | null
  owner_name?: string
  owner_id?: number
  updated_at: string
  [key: string]: unknown
}

export interface MatchResultItem {
  score: number
  breakdown: { priority: number; freshness: number; preference: number; price: number; credit: number }
  reasons: string[]
  available_quantity: number
  entity: MatchEntity
  full: boolean
}

export async function runMatch(params: { customer_id?: number; publication_id?: number }) {
  const { data } = await http.get('/match', { params })
  return data as { demand_type: string; demand_id: number; results: MatchResultItem[]; filtered: { supplier_id: number; name: string; reason: string }[] }
}

// ---------- 优先级 ----------
export interface Priority {
  id: number
  user_id: number
  entity_type: string
  entity_id: number
  priority: number
}

export async function listPriorities() {
  const { data } = await http.get('/priorities')
  return data as Priority[]
}
export async function setPriority(entity_type: string, entity_id: number, priority: number) {
  const { data } = await http.put('/priorities', { entity_type, entity_id, priority })
  return data as Priority
}
export async function clearPriority(entity_type: string, entity_id: number) {
  await http.delete(`/priorities/${entity_type}/${entity_id}`)
}

// ---------- 详情申请 ----------
export interface DetailRequest {
  id: number
  requester_id: number
  entity_type: string
  entity_id: number
  status: string
  note: string
  requested_at: string
}

export async function listDetailRequests(mine = '') {
  const { data } = await http.get('/detail-requests', { params: { mine } })
  return data as DetailRequest[]
}
export async function createDetailRequest(entity_type: string, entity_id: number, note = '') {
  const { data } = await http.post('/detail-requests', { entity_type, entity_id, note })
  return data as DetailRequest
}
export async function respondDetailRequest(id: number, action: 'approve' | 'reject') {
  const { data } = await http.post(`/detail-requests/${id}/${action}`, {})
  return data as DetailRequest
}
