from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class ProductLine(Base):
    __tablename__ = "product_lines"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    category: Mapped[str] = mapped_column(String(32), default="整机")  # 整机/板卡/其他
    status: Mapped[str] = mapped_column(String(16), default="active")
    remark: Mapped[str] = mapped_column(String(256), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class OverseasChain(Base):
    """海外链路方:同一条链路下可有多个国内供货方代表"""

    __tablename__ = "overseas_chains"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128))
    region: Mapped[str] = mapped_column(String(128), default="")
    contact_person: Mapped[str] = mapped_column(String(64), default="")
    contact_info: Mapped[str] = mapped_column(String(256), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    owner_id: Mapped[int] = mapped_column(Integer, index=True)
    last_editor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # 基础信息
    name: Mapped[str] = mapped_column(String(128), index=True)
    short_name: Mapped[str] = mapped_column(String(64), default="")
    reg_location: Mapped[str] = mapped_column(String(128), default="")
    credit_code: Mapped[str] = mapped_column(String(64), default="")
    established_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    registered_capital: Mapped[str] = mapped_column(String(64), default="")
    equity_structure: Mapped[str] = mapped_column(Text, default="")
    contacts: Mapped[list | None] = mapped_column(JSON, nullable=True)  # [{name,title,phone,wechat,email}]
    remark: Mapped[str] = mapped_column(Text, default="")
    # 链路归属
    chain_id: Mapped[int | None] = mapped_column(ForeignKey("overseas_chains.id"), nullable=True, index=True)
    chain_role: Mapped[str] = mapped_column(String(32), default="")  # 一手/二手/居间代表/其他
    parent_supplier_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 交易属性
    procurement_modes: Mapped[list | None] = mapped_column(JSON, nullable=True)  # [预付款, 信用证-国内, 信用证-跨境]
    goods_type: Mapped[str] = mapped_column(String(16), default="现货")  # 期货/现货/准现货
    price: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="CNY")
    price_valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    moq: Mapped[str] = mapped_column(String(64), default="")
    delivery_cycle: Mapped[str] = mapped_column(String(64), default="")
    payment_terms: Mapped[str] = mapped_column(String(256), default="")
    invoice_type: Mapped[str] = mapped_column(String(64), default="")
    # 反向保障
    guarantee_type: Mapped[str] = mapped_column(String(32), default="")  # 保函/先开后开/无/其他
    guarantee_ratio: Mapped[str] = mapped_column(String(32), default="")
    guarantee_issuer: Mapped[str] = mapped_column(String(16), default="")  # 企业/银行/保险公司
    guarantee_issuer_name: Mapped[str] = mapped_column(String(128), default="")
    guarantee_valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    financing_capacity: Mapped[str] = mapped_column(String(128), default="")
    guarantee_notes: Mapped[str] = mapped_column(Text, default="")
    # 合作评价
    coop_status: Mapped[str] = mapped_column(String(16), default="意向")  # 意向/洽谈中/合作中/暂停/终止
    deal_count: Mapped[int] = mapped_column(Integer, default=0)
    deal_amount: Mapped[float | None] = mapped_column(Numeric(16, 2), nullable=True)
    fulfillment_rate: Mapped[str] = mapped_column(String(16), default="")
    breach_count: Mapped[int] = mapped_column(Integer, default=0)
    credit_rating: Mapped[str] = mapped_column(String(8), default="")
    risk_notes: Mapped[str] = mapped_column(Text, default="")
    # 归属与版本
    owner_id: Mapped[int] = mapped_column(Integer, index=True)
    last_editor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class SupplierQuota(Base):
    __tablename__ = "supplier_quotas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), index=True)
    product_line_id: Mapped[int | None] = mapped_column(ForeignKey("product_lines.id"), nullable=True)
    batch_no: Mapped[str] = mapped_column(String(64), default="")
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    used_quantity: Mapped[int] = mapped_column(Integer, default=0)
    quota_start_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    quota_end_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="available")  # available/locked/used_up/expired
    remark: Mapped[str] = mapped_column(String(256), default="")
    created_by: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # 基础信息
    name: Mapped[str] = mapped_column(String(128), index=True)
    credit_code: Mapped[str] = mapped_column(String(64), default="")
    reg_location: Mapped[str] = mapped_column(String(128), default="")
    established_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    registered_capital: Mapped[str] = mapped_column(String(64), default="")
    industry: Mapped[str] = mapped_column(String(64), default="")
    contacts: Mapped[list | None] = mapped_column(JSON, nullable=True)
    remark: Mapped[str] = mapped_column(Text, default="")
    # 证照与账户(签约时维护)
    license_file: Mapped[str] = mapped_column(String(256), default="")
    account_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # {户名,开户行,账号}
    invoice_info: Mapped[str] = mapped_column(String(256), default="")
    # 交易意向
    intent_modes: Mapped[list | None] = mapped_column(JSON, nullable=True)  # [预付款, 信用证-国内, 信用证-跨境]
    intent_products: Mapped[list | None] = mapped_column(JSON, nullable=True)  # [{product_line_id, quantity}]
    intent_quantity: Mapped[str] = mapped_column(String(64), default="")
    budget_range: Mapped[str] = mapped_column(String(128), default="")
    expected_deal_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    goods_preference: Mapped[str] = mapped_column(String(16), default="")  # 现货/期货
    # 客户画像
    customer_type: Mapped[str] = mapped_column(String(32), default="")  # 终端使用方/贸易商/国资平台/民营
    purpose: Mapped[str] = mapped_column(String(32), default="")  # 自用/转售
    decision_chain: Mapped[str] = mapped_column(String(256), default="")
    payment_habit: Mapped[str] = mapped_column(String(128), default="")
    risk_preference: Mapped[str] = mapped_column(String(128), default="")
    value_grade: Mapped[str] = mapped_column(String(4), default="")  # A/B/C
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # 归属与版本
    owner_id: Mapped[int] = mapped_column(Integer, index=True)
    last_editor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class CapitalVerification(Base):
    """验资材料:四种方式,每种独立建档"""

    __tablename__ = "capital_verifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    verify_type: Mapped[str] = mapped_column(String(32))  # video/balance_photo/bank_certificate/guarantee_letter
    file_name: Mapped[str] = mapped_column(String(256), default="")
    file_path: Mapped[str] = mapped_column(String(256), default="")
    uploaded_by: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    material_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    amount: Mapped[str] = mapped_column(String(64), default="")
    ai_status: Mapped[str] = mapped_column(String(16), default="pending")  # pending/passed/flagged
    ai_report: Mapped[str] = mapped_column(Text, default="")
    review_status: Mapped[str] = mapped_column(String(16), default="pending")  # pending/approved/rejected
    reviewed_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    review_note: Mapped[str] = mapped_column(String(256), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class MiddleLayer(Base):
    __tablename__ = "middle_layers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    credit_code: Mapped[str] = mapped_column(String(64), default="")
    entity_nature: Mapped[str] = mapped_column(String(16), default="")  # 国资/民营/混合/其他
    layer_no: Mapped[int] = mapped_column(Integer, default=1)  # 第1层/第2层
    reg_location: Mapped[str] = mapped_column(String(128), default="")
    registered_capital: Mapped[str] = mapped_column(String(64), default="")
    contact_info: Mapped[str] = mapped_column(String(256), default="")
    purposes: Mapped[list | None] = mapped_column(JSON, nullable=True)  # [代开信用证,开保函,居间分账,意向金截流,其他]
    fee_rate: Mapped[str] = mapped_column(String(64), default="")
    settlement: Mapped[str] = mapped_column(String(128), default="")
    coop_status: Mapped[str] = mapped_column(String(16), default="意向")
    credit_rating: Mapped[str] = mapped_column(String(8), default="")
    risk_notes: Mapped[str] = mapped_column(Text, default="")
    remark: Mapped[str] = mapped_column(Text, default="")
    owner_id: Mapped[int] = mapped_column(Integer, index=True)
    last_editor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Communication(Base):
    """沟通记录:只增不改,append-only"""

    __tablename__ = "communications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(String(16), index=True)  # supplier/customer/middle
    entity_id: Mapped[int] = mapped_column(Integer, index=True)
    comm_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    channel: Mapped[str] = mapped_column(String(16), default="")  # 电话/微信/面谈/会议/其他
    participants: Mapped[str] = mapped_column(String(128), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    next_step: Mapped[str] = mapped_column(String(256), default="")
    follow_up_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    attachment: Mapped[str] = mapped_column(String(256), default="")
    created_by: Mapped[int] = mapped_column(Integer, default=0)
    created_by_name: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DataShare(Base):
    """数据共享:申请-审批制"""

    __tablename__ = "data_shares"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    requester_id: Mapped[int] = mapped_column(Integer, index=True)
    target_id: Mapped[int] = mapped_column(Integer, index=True)
    scopes: Mapped[list | None] = mapped_column(JSON, nullable=True)  # [all]/[supplier, customer, middle]
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending/active/rejected/cancelled
    note: Mapped[str] = mapped_column(String(256), default="")
    requested_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    responded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    responded_by: Mapped[int | None] = mapped_column(Integer, nullable=True)


class StoredFile(Base):
    __tablename__ = "stored_files"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    stored_name: Mapped[str] = mapped_column(String(128), unique=True)
    original_name: Mapped[str] = mapped_column(String(256), default="")
    uploader_id: Mapped[int] = mapped_column(Integer, default=0)
    entity_type: Mapped[str] = mapped_column(String(16), default="")
    entity_id: Mapped[int] = mapped_column(Integer, default=0)
    size: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Publication(Base):
    """供需看板发布:默认全员可见,可设私密;到期自动关闭"""

    __tablename__ = "publications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    type: Mapped[str] = mapped_column(String(16), index=True)  # demand 采购需求 / supply 供货信息
    product_line_id: Mapped[int | None] = mapped_column(ForeignKey("product_lines.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(128))
    quantity: Mapped[str] = mapped_column(String(64), default="")
    price_min: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    price_max: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="CNY")
    validity_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    visibility: Mapped[str] = mapped_column(String(16), default="public")  # public/private
    status: Mapped[str] = mapped_column(String(16), default="active")  # active/closed/dealt
    content: Mapped[str] = mapped_column(Text, default="")
    intent_modes: Mapped[list | None] = mapped_column(JSON, nullable=True)
    goods_preference: Mapped[str] = mapped_column(String(16), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class UserPriority(Base):
    """用户对上游供货方/下游客户的自设优先级(1-9),未设置按更新时间排序"""

    __tablename__ = "user_priorities"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    entity_type: Mapped[str] = mapped_column(String(16))  # supplier/customer
    entity_id: Mapped[int] = mapped_column(Integer)
    priority: Mapped[int] = mapped_column(Integer, default=5)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class DetailRequest(Base):
    """匹配结果中他人数据查看全量的申请-审批"""

    __tablename__ = "detail_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    requester_id: Mapped[int] = mapped_column(Integer, index=True)
    entity_type: Mapped[str] = mapped_column(String(16))  # supplier/customer
    entity_id: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending/approved/rejected
    note: Mapped[str] = mapped_column(String(256), default="")
    requested_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    responded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    responded_by: Mapped[int | None] = mapped_column(Integer, nullable=True)


class MatchResult(Base):
    """匹配结果快照:每次为某需求重算时重建"""

    __tablename__ = "match_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    demand_type: Mapped[str] = mapped_column(String(16), index=True)  # customer/publication
    demand_id: Mapped[int] = mapped_column(Integer, index=True)
    supplier_id: Mapped[int] = mapped_column(Integer, index=True)
    score: Mapped[int] = mapped_column(Integer, default=0)
    breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reasons: Mapped[list | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="new")  # new/viewed/accepted/ignored
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(String(64), index=True)
    product_line_id: Mapped[int | None] = mapped_column(ForeignKey("product_lines.id"), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    unit_price: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    total_amount: Mapped[float | None] = mapped_column(Numeric(16, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="CNY")
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"), nullable=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    middle_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    payment_mode: Mapped[str] = mapped_column(String(32), default="")
    contract_no: Mapped[str] = mapped_column(String(128), default="")
    contract_file: Mapped[str] = mapped_column(String(256), default="")
    status: Mapped[str] = mapped_column(String(32), default="registered", index=True)
    pre_breach_status: Mapped[str] = mapped_column(String(32), default="")
    signed_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    owner_id: Mapped[int] = mapped_column(Integer, index=True)
    last_editor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class OrderTrack(Base):
    """订单跟踪事件:只增不改"""

    __tablename__ = "order_tracks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    category: Mapped[str] = mapped_column(String(16), default="其他")  # 货源/资金/到货/交付/违约/其他
    title: Mapped[str] = mapped_column(String(128), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    attachment: Mapped[str] = mapped_column(String(256), default="")
    created_by: Mapped[int] = mapped_column(Integer, default=0)
    created_by_name: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Breach(Base):
    """违约事项独立跟踪"""

    __tablename__ = "breaches"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    breach_party: Mapped[str] = mapped_column(String(32), default="")  # 上游/下游/中间层/其他
    breach_content: Mapped[str] = mapped_column(Text, default="")
    solution: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="处理中")  # 处理中/已解决/已关闭
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class DealPlan(Base):
    """成本收益:交易链路测算方案"""

    __tablename__ = "deal_plans"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(128))
    order_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    product_line_id: Mapped[int | None] = mapped_column(ForeignKey("product_lines.id"), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    upstream_price: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)  # 上游单价
    downstream_price: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)  # 下游单价
    currency: Mapped[str] = mapped_column(String(8), default="CNY")
    payment_mode: Mapped[str] = mapped_column(String(32), default="预付款")  # 预付款/信用证-国内/信用证-跨境
    wrapped_price: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)  # 与上游的包裹协议价(≥上游真实价)
    supplier_fee_fixed: Mapped[float | None] = mapped_column(Numeric(16, 2), nullable=True)  # 上游居间定额(交易完成后支付)
    upfront_percent: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)  # 居间前置比例(基于中间层包裹收益,通常10-30%)
    lc_agent_middle: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 代开证中间层节点
    lc_deposit_percent: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)  # 开证保证金比例
    lc_fee_percent: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)  # 代开证费率(1-3%)
    status: Mapped[str] = mapped_column(String(16), default="draft")  # draft/confirmed
    owner_id: Mapped[int] = mapped_column(Integer, index=True)
    last_editor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class DealNode(Base):
    """链路参与方节点:customer / middle / supplier,可多个中间层"""

    __tablename__ = "deal_nodes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("deal_plans.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))  # customer/middle/supplier
    name: Mapped[str] = mapped_column(String(128))
    entity_type: Mapped[str] = mapped_column(String(16), default="")  # supplier/customer/middle
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seq: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str] = mapped_column(String(256), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DealFlow(Base):
    """资金/保函动作流,按 seq 排序,用户自行增删排序"""

    __tablename__ = "deal_flows"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("deal_plans.id"), index=True)
    seq: Mapped[int] = mapped_column(Integer, default=0)
    flow_type: Mapped[str] = mapped_column(String(24))  # payment/guarantee/lc_issue/margin/upfront_fee/lc_fee/goods/other
    label: Mapped[str] = mapped_column(String(128), default="")
    from_node_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    to_node_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    amount_type: Mapped[str] = mapped_column(String(16), default="fixed")  # fixed/percent
    amount: Mapped[float | None] = mapped_column(Numeric(16, 2), nullable=True)
    percent: Mapped[float | None] = mapped_column(Numeric(8, 3), nullable=True)  # 百分比(如 20 = 20%)
    base: Mapped[str] = mapped_column(String(16), default="downstream_total")  # 比例基数:downstream_total/upstream_total/spread
    note: Mapped[str] = mapped_column(String(256), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class OrderDocument(Base):
    """订单合同文件:模版/定稿扫描件,记录业务全生命周期"""

    __tablename__ = "order_documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    doc_type: Mapped[str] = mapped_column(String(24), default="其他")  # 模版/定稿扫描件/补充协议/其他
    file_name: Mapped[str] = mapped_column(String(256), default="")
    file_path: Mapped[str] = mapped_column(String(256), default="")
    note: Mapped[str] = mapped_column(String(256), default="")
    uploaded_by: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_by_name: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DutyReport(Base):
    """值班机器人简报"""

    __tablename__ = "duty_reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    content: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ai_text: Mapped[str] = mapped_column(Text, default="")
    is_read: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
