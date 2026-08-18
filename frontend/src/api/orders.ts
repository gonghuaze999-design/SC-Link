import http from './http'

// ---------- 订单 ----------
export interface Order {
  id: number
  order_no: string
  product_line_id: number | null
  quantity: number
  unit_price: number | null
  total_amount: number | null
  currency: string
  supplier_id: number | null
  customer_id: number | null
  middle_ids: number[] | null
  payment_mode: string
  contract_no: string
  contract_file: string
  status: string
  pre_breach_status: string
  signed_at: string | null
  owner_id: number
  version: number
  created_at: string
  updated_at: string
}

export const ORDER_STATUSES: Record<string, { label: string; cls: string }> = {
  registered: { label: '已录入', cls: 'bg-slate-100 text-slate-600' },
  sourcing: { label: '货源确认中', cls: 'bg-blue-50 text-blue-600' },
  sourced: { label: '货源已确认', cls: 'bg-cyan-50 text-cyan-600' },
  paying: { label: '付款中', cls: 'bg-indigo-50 text-indigo-600' },
  paid: { label: '已付款', cls: 'bg-green-50 text-green-600' },
  arrived: { label: '到货', cls: 'bg-teal-50 text-teal-600' },
  delivered: { label: '已交付', cls: 'bg-emerald-50 text-emerald-600' },
  done: { label: '已完成', cls: 'bg-green-100 text-green-700' },
  breach: { label: '违约', cls: 'bg-red-50 text-red-600' },
  breach_processing: { label: '违约处理中', cls: 'bg-amber-50 text-amber-600' },
  closed: { label: '已关闭', cls: 'bg-slate-100 text-slate-500' },
}

export const TRACK_CATEGORIES: Record<string, string> = {
  货源: '货源', 资金: '资金', 到货: '到货', 交付: '交付', 违约: '违约', 其他: '其他',
}
export const TRACK_CAT_CLS: Record<string, string> = {
  货源: 'bg-blue-50 text-blue-600',
  资金: 'bg-green-50 text-green-600',
  到货: 'bg-cyan-50 text-cyan-600',
  交付: 'bg-purple-50 text-purple-600',
  违约: 'bg-red-50 text-red-600',
  其他: 'bg-slate-100 text-slate-500',
}

export async function listOrders(params: { status?: string; keyword?: string } = {}) {
  const { data } = await http.get('/orders', { params })
  return data as Order[]
}
export async function createOrder(payload: Partial<Order>) {
  const { data } = await http.post('/orders', payload)
  return data as Order
}
export async function updateOrder(id: number, payload: Partial<Order> & { version: number }) {
  const { data } = await http.patch(`/orders/${id}`, payload)
  return data as Order
}
export async function changeOrderStatus(id: number, status: string) {
  const { data } = await http.post(`/orders/${id}/status`, { status })
  return data as Order
}
export async function deleteOrder(id: number) {
  await http.delete(`/orders/${id}`)
}

// ---------- 跟踪事件 ----------
export interface Track {
  id: number
  order_id: number
  category: string
  title: string
  content: string
  attachment: string
  created_by_name: string
  created_at: string
}

export async function listTracks(orderId: number) {
  const { data } = await http.get(`/orders/${orderId}/tracks`)
  return data as Track[]
}
export async function createTrack(orderId: number, payload: Partial<Track>) {
  const { data } = await http.post(`/orders/${orderId}/tracks`, payload)
  return data as Track
}

// ---------- 违约事项 ----------
export interface Breach {
  id: number
  order_id: number
  breach_party: string
  breach_content: string
  solution: string
  status: string
  updated_at: string
}

export async function listBreaches(orderId: number) {
  const { data } = await http.get(`/orders/${orderId}/breaches`)
  return data as Breach[]
}
export async function createBreach(orderId: number, payload: Partial<Breach>) {
  const { data } = await http.post(`/orders/${orderId}/breaches`, payload)
  return data as Breach
}
export async function updateBreach(id: number, payload: Partial<Breach>) {
  const { data } = await http.patch(`/breaches/${id}`, payload)
  return data as Breach
}

// ---------- 跟单 AI ----------
export async function aiOrderSummary(orderId: number) {
  const { data } = await http.post(`/orders/${orderId}/ai-summary`, {})
  return (data as { summary: string }).summary
}
export async function aiExtractTracks(orderId: number, text: string) {
  const { data } = await http.post(`/orders/${orderId}/ai-extract`, { text })
  return (data as { events: { category: string; title: string; content: string; next_action: string }[] }).events
}

// ---------- 分析中台 ----------
export interface AnalyticsOverview {
  supplier_count: number
  customer_count: number
  chain_count: number
  middle_count: number
  verified_count: number
  verified_rate: number
  active_orders: number
  month_amount: number
  expiring_quotas: { quota_id: number; supplier: string; batch_no: string; end_at: string; remain: number }[]
  monthly_trend: { month: string; suppliers: number; customers: number }[]
  dynamics: { username: string; action: string; entity_type: string; entity_id: string; detail: string; at: string }[]
}

export async function fetchAnalytics() {
  const { data } = await http.get('/analytics/overview')
  return data as AnalyticsOverview
}
