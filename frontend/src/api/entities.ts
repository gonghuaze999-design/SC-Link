import http from './http'

// ---------- 产品线 ----------
export interface ProductLine {
  id: number
  name: string
  category: string
  status: string
  remark: string
}

export async function listProductLines() {
  const { data } = await http.get('/product-lines')
  return data as ProductLine[]
}

// ---------- 链路方 ----------
export interface Chain {
  id: number
  name: string
  region: string
  contact_person: string
  contact_info: string
  description: string
  owner_id: number
  last_editor_id: number | null
  version: number
  updated_at: string
}

export async function listChains() {
  const { data } = await http.get('/chains')
  return data as Chain[]
}
export async function createChain(payload: Partial<Chain>) {
  const { data } = await http.post('/chains', payload)
  return data as Chain
}
export async function updateChain(id: number, payload: Partial<Chain> & { version: number }) {
  const { data } = await http.patch(`/chains/${id}`, payload)
  return data as Chain
}
export async function deleteChain(id: number) {
  await http.delete(`/chains/${id}`)
}

// ---------- 上游供货方 ----------
export interface Supplier {
  id: number
  name: string
  short_name: string
  reg_location: string
  credit_code: string
  established_at: string | null
  registered_capital: string
  equity_structure: string
  contacts: { name: string; title: string; phone: string; wechat: string; email: string }[] | null
  remark: string
  chain_id: number | null
  chain_role: string
  parent_supplier_id: number | null
  procurement_modes: string[] | null
  goods_type: string
  price: number | null
  currency: string
  price_valid_until: string | null
  price_valid_days: number | null
  moq: string
  delivery_cycle: string
  payment_terms: string
  invoice_type: string
  account_info: Record<string, string> | null
  guarantee_type: string
  guarantee_ratio: string
  guarantee_issuer: string
  guarantee_issuer_name: string
  guarantee_valid_until: string | null
  financing_capacity: string
  guarantee_notes: string
  coop_status: string
  deal_count: number
  deal_amount: number | null
  fulfillment_rate: string
  breach_count: number
  credit_rating: string
  risk_notes: string
  owner_id: number
  last_editor_id: number | null
  version: number
  created_at: string
  updated_at: string
}

export async function listSuppliers(params: { keyword?: string; goods_type?: string; chain_id?: number } = {}) {
  const { data } = await http.get('/suppliers', { params })
  return data as Supplier[]
}
export async function createSupplier(payload: Partial<Supplier>) {
  const { data } = await http.post('/suppliers', payload)
  return data as Supplier
}
export async function updateSupplier(id: number, payload: Partial<Supplier> & { version: number }) {
  const { data } = await http.patch(`/suppliers/${id}`, payload)
  return data as Supplier
}
export async function deleteSupplier(id: number) {
  await http.delete(`/suppliers/${id}`)
}

// ---------- 配额 ----------
export interface Quota {
  id: number
  supplier_id: number
  product_line_id: number | null
  batch_no: string
  quantity: number
  used_quantity: number
  quota_start_at: string | null
  quota_end_at: string | null
  status: string
  remark: string
  created_at: string
}

export async function listQuotas(supplierId: number) {
  const { data } = await http.get(`/suppliers/${supplierId}/quotas`)
  return data as Quota[]
}
export async function createQuota(supplierId: number, payload: Partial<Quota>) {
  const { data } = await http.post(`/suppliers/${supplierId}/quotas`, payload)
  return data as Quota
}
export async function updateQuota(id: number, payload: Partial<Quota>) {
  const { data } = await http.patch(`/quotas/${id}`, payload)
  return data as Quota
}
export async function deleteQuota(id: number) {
  await http.delete(`/quotas/${id}`)
}

// ---------- 下游客户 ----------
export interface Customer {
  verified: boolean

  id: number
  name: string
  credit_code: string
  reg_location: string
  established_at: string | null
  registered_capital: string
  industry: string
  contacts: { name: string; title: string; phone: string; wechat: string; email: string }[] | null
  remark: string
  license_file: string
  account_info: Record<string, string> | null
  invoice_info: string
  invoice_detail: Record<string, string> | null
  intent_modes: string[] | null
  intent_products: { product_line_id: number; quantity: string }[] | null
  intent_quantity: string
  budget_range: string
  expected_deal_at: string | null
  goods_preference: string
  customer_type: string
  purpose: string
  decision_chain: string
  payment_habit: string
  risk_preference: string
  value_grade: string
  tags: string[] | null
  owner_id: number
  last_editor_id: number | null
  version: number
  updated_at: string
}

export async function listCustomers(params: { keyword?: string; verified?: string } = {}) {
  const { data } = await http.get('/customers', { params })
  return data as Customer[]
}
export async function createCustomer(payload: Partial<Customer>) {
  const { data } = await http.post('/customers', payload)
  return data as Customer
}
export async function updateCustomer(id: number, payload: Partial<Customer> & { version: number }) {
  const { data } = await http.patch(`/customers/${id}`, payload)
  return data as Customer
}
export async function deleteCustomer(id: number) {
  await http.delete(`/customers/${id}`)
}

// ---------- 验资材料 ----------
export interface Verification {
  id: number
  customer_id: number
  verify_type: string
  file_name: string
  file_path: string
  uploaded_by: number
  uploaded_at: string
  material_date: string | null
  valid_until: string | null
  amount: string
  ai_status: string
  ai_report: string
  review_status: string
  reviewed_by: number | null
  reviewed_at: string | null
  review_note: string
}

export async function listVerifications(customerId: number) {
  const { data } = await http.get(`/customers/${customerId}/verifications`)
  return data as Verification[]
}
export async function createVerification(customerId: number, payload: Partial<Verification>) {
  const { data } = await http.post(`/customers/${customerId}/verifications`, payload)
  return data as Verification
}
export async function reviewVerification(id: number, review_status: string, review_note: string) {
  const { data } = await http.patch(`/verifications/${id}`, { review_status, review_note })
  return data as Verification
}
export async function deleteVerification(id: number) {
  await http.delete(`/verifications/${id}`)
}

export async function uploadFile(file: File, entityType: string, entityId: number) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await http.post(`/files?entity_type=${entityType}&entity_id=${entityId}`, form)
  return data as { id: number; stored_name: string; original_name: string }
}

// ---------- 中间层 ----------
export interface Middle {
  id: number
  name: string
  credit_code: string
  entity_nature: string
  layer_no: number
  reg_location: string
  registered_capital: string
  contact_info: string
  account_info: Record<string, string> | null
  invoice_detail: Record<string, string> | null
  purposes: string[] | null
  fee_rate: string
  settlement: string
  coop_status: string
  credit_rating: string
  risk_notes: string
  remark: string
  owner_id: number
  last_editor_id: number | null
  version: number
  updated_at: string
}

export async function listMiddles(params: { keyword?: string } = {}) {
  const { data } = await http.get('/middles', { params })
  return data as Middle[]
}
export async function createMiddle(payload: Partial<Middle>) {
  const { data } = await http.post('/middles', payload)
  return data as Middle
}
export async function updateMiddle(id: number, payload: Partial<Middle> & { version: number }) {
  const { data } = await http.patch(`/middles/${id}`, payload)
  return data as Middle
}
export async function deleteMiddle(id: number) {
  await http.delete(`/middles/${id}`)
}

// ---------- 沟通记录 ----------
export interface Communication {
  id: number
  entity_type: string
  entity_id: number
  comm_time: string | null
  channel: string
  participants: string
  content: string
  next_step: string
  follow_up_at: string | null
  attachment: string
  created_by_name: string
  created_at: string
}

export async function listCommunications(entityType: string, entityId: number) {
  const { data } = await http.get('/communications', { params: { entity_type: entityType, entity_id: entityId } })
  return data as Communication[]
}
export async function createCommunication(entityType: string, entityId: number, payload: Partial<Communication>) {
  const { data } = await http.post(`/communications?entity_type=${entityType}&entity_id=${entityId}`, payload)
  return data as Communication
}

// ---------- 数据共享 ----------
export interface Share {
  id: number
  requester_id: number
  target_id: number
  scopes: string[] | null
  status: string
  note: string
  requested_at: string
  responded_at: string | null
}

export async function listShares() {
  const { data } = await http.get('/shares')
  return data as Share[]
}
export async function createShare(target_id: number, scopes: string[], note: string) {
  const { data } = await http.post('/shares', { target_id, scopes, note })
  return data as Share
}
export async function respondShare(id: number, action: 'approve' | 'reject', note = '') {
  const { data } = await http.post(`/shares/${id}/${action}`, { note })
  return data as Share
}
export async function cancelShare(id: number) {
  const { data } = await http.post(`/shares/${id}/cancel`, {})
  return data as Share
}

export async function listUserOptions() {
  const { data } = await http.get('/users/options')
  return data as { id: number; username: string; display_name: string }[]
}
