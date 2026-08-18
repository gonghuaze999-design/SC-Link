from datetime import date, datetime

from pydantic import BaseModel, Field


# ---------- 产品线 ----------
class ProductLineOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    category: str
    status: str
    remark: str


class ProductLineIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    category: str = "整机"
    status: str = "active"
    remark: str = ""


# ---------- 海外链路方 ----------
class ChainOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    region: str
    contact_person: str
    contact_info: str
    description: str
    owner_id: int
    last_editor_id: int | None
    version: int
    created_at: datetime
    updated_at: datetime


class ChainIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    region: str = ""
    contact_person: str = ""
    contact_info: str = ""
    description: str = ""


class ChainUpdate(BaseModel):
    name: str | None = None
    region: str | None = None
    contact_person: str | None = None
    contact_info: str | None = None
    description: str | None = None
    version: int


# ---------- 上游供货方 ----------
class SupplierOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    short_name: str
    reg_location: str
    credit_code: str
    established_at: date | None
    registered_capital: str
    equity_structure: str
    contacts: list | None
    remark: str
    chain_id: int | None
    chain_role: str
    parent_supplier_id: int | None
    procurement_modes: list | None
    goods_type: str
    price: float | None
    currency: str
    price_valid_until: date | None
    moq: str
    delivery_cycle: str
    payment_terms: str
    invoice_type: str
    guarantee_type: str
    guarantee_ratio: str
    guarantee_issuer: str
    guarantee_issuer_name: str
    guarantee_valid_until: date | None
    financing_capacity: str
    guarantee_notes: str
    coop_status: str
    deal_count: int
    deal_amount: float | None
    fulfillment_rate: str
    breach_count: int
    credit_rating: str
    risk_notes: str
    owner_id: int
    last_editor_id: int | None
    version: int
    created_at: datetime
    updated_at: datetime


class SupplierIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    short_name: str = ""
    reg_location: str = ""
    credit_code: str = ""
    established_at: date | None = None
    registered_capital: str = ""
    equity_structure: str = ""
    contacts: list | None = None
    remark: str = ""
    chain_id: int | None = None
    chain_role: str = ""
    parent_supplier_id: int | None = None
    procurement_modes: list | None = None
    goods_type: str = "现货"
    price: float | None = None
    currency: str = "CNY"
    price_valid_until: date | None = None
    moq: str = ""
    delivery_cycle: str = ""
    payment_terms: str = ""
    invoice_type: str = ""
    guarantee_type: str = ""
    guarantee_ratio: str = ""
    guarantee_issuer: str = ""
    guarantee_issuer_name: str = ""
    guarantee_valid_until: date | None = None
    financing_capacity: str = ""
    guarantee_notes: str = ""
    coop_status: str = "意向"
    deal_count: int = 0
    deal_amount: float | None = None
    fulfillment_rate: str = ""
    breach_count: int = 0
    credit_rating: str = ""
    risk_notes: str = ""


class SupplierUpdate(SupplierIn):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    version: int


# ---------- 批次配额 ----------
class QuotaOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    supplier_id: int
    product_line_id: int | None
    batch_no: str
    quantity: int
    used_quantity: int
    quota_start_at: date | None
    quota_end_at: date | None
    status: str
    remark: str
    created_by: int
    created_at: datetime


class QuotaIn(BaseModel):
    product_line_id: int | None = None
    batch_no: str = ""
    quantity: int = Field(ge=0)
    used_quantity: int = Field(default=0, ge=0)
    quota_start_at: date | None = None
    quota_end_at: date | None = None
    status: str = "available"
    remark: str = ""


class QuotaUpdate(BaseModel):
    product_line_id: int | None = None
    batch_no: str | None = None
    quantity: int | None = Field(default=None, ge=0)
    used_quantity: int | None = Field(default=None, ge=0)
    quota_start_at: date | None = None
    quota_end_at: date | None = None
    status: str | None = None
    remark: str | None = None


# ---------- 下游客户 ----------
class CustomerOut(BaseModel):
    model_config = {"from_attributes": True}

    verified: bool = False

    id: int
    name: str
    credit_code: str
    reg_location: str
    established_at: date | None
    registered_capital: str
    industry: str
    contacts: list | None
    remark: str
    license_file: str
    account_info: dict | None
    invoice_info: str
    intent_modes: list | None
    intent_products: list | None
    intent_quantity: str
    budget_range: str
    expected_deal_at: date | None
    goods_preference: str
    customer_type: str
    purpose: str
    decision_chain: str
    payment_habit: str
    risk_preference: str
    value_grade: str
    tags: list | None
    owner_id: int
    last_editor_id: int | None
    version: int
    created_at: datetime
    updated_at: datetime


class CustomerIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    credit_code: str = ""
    reg_location: str = ""
    established_at: date | None = None
    registered_capital: str = ""
    industry: str = ""
    contacts: list | None = None
    remark: str = ""
    license_file: str = ""
    account_info: dict | None = None
    invoice_info: str = ""
    intent_modes: list | None = None
    intent_products: list | None = None
    intent_quantity: str = ""
    budget_range: str = ""
    expected_deal_at: date | None = None
    goods_preference: str = ""
    customer_type: str = ""
    purpose: str = ""
    decision_chain: str = ""
    payment_habit: str = ""
    risk_preference: str = ""
    value_grade: str = ""
    tags: list | None = None


class CustomerUpdate(CustomerIn):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    version: int


# ---------- 验资材料 ----------
class VerificationOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    customer_id: int
    verify_type: str
    file_name: str
    file_path: str
    uploaded_by: int
    uploaded_at: datetime
    material_date: date | None
    valid_until: date | None
    amount: str
    ai_status: str
    ai_report: str
    review_status: str
    reviewed_by: int | None
    reviewed_at: datetime | None
    review_note: str


class VerificationIn(BaseModel):
    verify_type: str = Field(pattern="^(video|balance_photo|bank_certificate|guarantee_letter)$")
    file_name: str = ""
    file_path: str = ""
    material_date: date | None = None
    valid_until: date | None = None
    amount: str = ""


class VerificationReview(BaseModel):
    review_status: str = Field(pattern="^(approved|rejected)$")
    review_note: str = ""


# ---------- 中间层 ----------
class MiddleOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    credit_code: str
    entity_nature: str
    layer_no: int
    reg_location: str
    registered_capital: str
    contact_info: str
    purposes: list | None
    fee_rate: str
    settlement: str
    coop_status: str
    credit_rating: str
    risk_notes: str
    remark: str
    owner_id: int
    last_editor_id: int | None
    version: int
    created_at: datetime
    updated_at: datetime


class MiddleIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    credit_code: str = ""
    entity_nature: str = ""
    layer_no: int = Field(default=1, ge=1, le=2)
    reg_location: str = ""
    registered_capital: str = ""
    contact_info: str = ""
    purposes: list | None = None
    fee_rate: str = ""
    settlement: str = ""
    coop_status: str = "意向"
    credit_rating: str = ""
    risk_notes: str = ""
    remark: str = ""


class MiddleUpdate(MiddleIn):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    version: int


# ---------- 沟通记录 ----------
class CommunicationOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    entity_type: str
    entity_id: int
    comm_time: datetime | None
    channel: str
    participants: str
    content: str
    next_step: str
    follow_up_at: datetime | None
    attachment: str
    created_by: int
    created_by_name: str
    created_at: datetime


class CommunicationIn(BaseModel):
    comm_time: datetime | None = None
    channel: str = ""
    participants: str = ""
    content: str = Field(min_length=1, max_length=10000)
    next_step: str = ""
    follow_up_at: datetime | None = None
    attachment: str = ""


# ---------- 数据共享 ----------
class ShareOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    requester_id: int
    target_id: int
    scopes: list | None
    status: str
    note: str
    requested_at: datetime
    responded_at: datetime | None
    responded_by: int | None


class ShareIn(BaseModel):
    target_id: int
    scopes: list[str] = ["all"]
    note: str = ""


class ShareRespond(BaseModel):
    note: str = ""
