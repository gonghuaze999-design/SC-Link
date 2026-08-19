import http from './http'

// ---------- 交易方案 ----------
export interface DealPlan {
  id: number
  title: string
  order_id: number | null
  product_line_id: number | null
  quantity: number
  upstream_price: number | null
  downstream_price: number | null
  currency: string
  payment_mode: string
  lc_agent_middle: number | null
  lc_deposit_percent: number | null
  lc_fee_percent: number | null
  status: string
  owner_id: number
  version: number
  updated_at: string
}

export interface DealNode {
  id: number
  plan_id: number
  role: string
  name: string
  entity_type: string
  entity_id: number | null
  seq: number
  note: string
}

export interface DealFlow {
  id: number
  plan_id: number
  seq: number
  flow_type: string
  label: string
  from_node_id: number | null
  to_node_id: number | null
  amount_type: string
  amount: number | null
  percent: number | null
  base: string
  note: string
}

export interface DealCompute {
  totals: { downstream_total: number; upstream_total: number; spread: number }
  spread: number
  nodes: { node_id: number; role: string; name: string; seq: number; receive_total: number; paid_total: number; net: number; held_peak: number; held_final: number }[]
  middle_metrics: { node_id: number; name: string; receive_total: number; paid_total: number; held_peak: number; held_final: number; upfront_fee: number }[]
  lc_cost: { deposit: number; fee: number; total: number } | null
}

export async function listDealPlans() {
  const { data } = await http.get('/deal-plans')
  return data as DealPlan[]
}
export async function createDealPlan(payload: Partial<DealPlan>) {
  const { data } = await http.post('/deal-plans', payload)
  return data as DealPlan
}
export async function updateDealPlan(id: number, payload: Partial<DealPlan> & { version: number }) {
  const { data } = await http.patch(`/deal-plans/${id}`, payload)
  return data as DealPlan
}
export async function deleteDealPlan(id: number) {
  await http.delete(`/deal-plans/${id}`)
}
export async function listNodes(planId: number) {
  const { data } = await http.get(`/deal-plans/${planId}/nodes`)
  return data as DealNode[]
}
export async function createNode(planId: number, payload: Partial<DealNode>) {
  const { data } = await http.post(`/deal-plans/${planId}/nodes`, payload)
  return data as DealNode
}
export async function deleteNode(id: number) {
  await http.delete(`/deal-nodes/${id}`)
}
export async function listFlows(planId: number) {
  const { data } = await http.get(`/deal-plans/${planId}/flows`)
  return data as DealFlow[]
}
export async function createFlow(planId: number, payload: Partial<DealFlow>) {
  const { data } = await http.post(`/deal-plans/${planId}/flows`, payload)
  return data as DealFlow
}
export async function updateFlow(id: number, payload: Partial<DealFlow>) {
  const { data } = await http.patch(`/deal-flows/${id}`, payload)
  return data as DealFlow
}
export async function deleteFlow(id: number) {
  await http.delete(`/deal-flows/${id}`)
}
export async function computePlan(planId: number) {
  const { data } = await http.get(`/deal-plans/${planId}/compute`)
  return data as DealCompute
}

// ---------- 合同文件 ----------
export interface OrderDoc {
  id: number
  order_id: number
  doc_type: string
  file_name: string
  file_path: string
  note: string
  uploaded_by_name: string
  created_at: string
}

export async function listOrderDocs(orderId: number) {
  const { data } = await http.get(`/orders/${orderId}/documents`)
  return data as OrderDoc[]
}
export async function createOrderDoc(orderId: number, payload: Partial<OrderDoc>) {
  const { data } = await http.post(`/orders/${orderId}/documents`, payload)
  return data as OrderDoc
}
export async function deleteOrderDoc(id: number) {
  await http.delete(`/order-documents/${id}`)
}

// ---------- 值班机器人 ----------
export interface DutyReport {
  id: number
  content: {
    matches: { demand: string; publication_id?: number; customer_id?: number; top: { name: string; score: number; avail: number }[] }[]
    stale: { type: string; name: string; days: number }[]
    risks: { type: string; detail: string }[]
  }
  ai_text: string
  is_read: boolean
  created_at: string
}

export async function latestDuty() {
  const { data } = await http.get('/duty/reports/latest')
  return data as { report: DutyReport | null; unread: number }
}
export async function listDuty(limit = 20) {
  const { data } = await http.get('/duty/reports', { params: { limit } })
  return data as DutyReport[]
}
export async function runDuty() {
  const { data } = await http.post('/duty/run', {}, { timeout: 90000 })
  return data as { report: DutyReport }
}
export async function markDutyRead(id: number) {
  await http.post(`/duty/reports/${id}/read`, {})
}
