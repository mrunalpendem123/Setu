from __future__ import annotations

import re
from datetime import datetime
from typing import List, Optional, Dict, Any, Literal, Union

from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator


class Address(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    line_one: str
    line_two: Optional[str] = None
    city: str
    state: str
    country: str = Field(min_length=2, max_length=2)
    postal_code: str
    phone_number: Optional[str] = None

    @field_validator("country")
    @classmethod
    def country_must_be_india(cls, v: str) -> str:
        if v.upper() != "IN":
            raise ValueError("country must be 'IN' for India")
        return v.upper()

    @field_validator("postal_code")
    @classmethod
    def validate_pin_code(cls, v: str) -> str:
        if not re.match(r"^[1-9][0-9]{5}$", v):
            raise ValueError("postal_code must be a valid 6-digit Indian PIN code")
        return v

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not re.match(r"^\+91[6-9]\d{9}$", v):
            raise ValueError("phone_number must be a valid Indian mobile number in E.164 format (+91XXXXXXXXXX)")
        return v


class GSTMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gstin: Optional[str] = None
    hsn_code: Optional[str] = None
    tax_label: str = "GST"
    tax_rate_pct: float = 18.0


BuyerAccountType = Literal["guest", "registered", "business"]
BuyerAuthenticationStatus = Literal["unverified", "verified", "3ds_authenticated"]


class Buyer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = None          # full name (for backward compatibility)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    account_type: BuyerAccountType = "guest"
    authentication_status: BuyerAuthenticationStatus = "unverified"


class ItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    quantity: int = Field(ge=1)


class PaymentHandlerDeclaration(BaseModel):
    """A payment handler declared by the agent or supported by the merchant."""
    model_config = ConfigDict(extra="allow")

    id: str                             # reverse-DNS: "com.hyperswitch.upi"
    version: str                        # "2026-02-24"
    psp: str                            # "hyperswitch"
    requires_delegate_payment: bool = True
    requires_pci_compliance: bool = False
    spec_uri: Optional[str] = None      # URI to the handler's machine-readable spec
    instrument_schema: Optional[Dict[str, Any]] = None  # JSON Schema for instrument params


class AgentCapabilities(BaseModel):
    """Capabilities declared by the agent in the checkout create request."""
    model_config = ConfigDict(extra="allow")

    payment_methods: List[str] = []     # ["card", "upi_collect", "upi_intent", "upi_qr"]
    payment_handlers: List[PaymentHandlerDeclaration] = []
    extensions: List[str] = []         # ["india_gst", "upi_vpa", "discounts"]
    locale: Optional[str] = None       # "hi-IN", "en-IN"
    timezone: Optional[str] = None     # "Asia/Kolkata"


class NegotiatedCapabilities(BaseModel):
    """Capabilities returned by the merchant after intersecting with agent declaration."""
    model_config = ConfigDict(extra="forbid")

    payment_methods: List[str]
    payment_handlers: List[PaymentHandlerDeclaration]
    extensions: List[str]
    locale: Optional[str] = None
    timezone: Optional[str] = None


class CheckoutSessionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: List[ItemInput]
    buyer_token: Optional[str] = None
    fulfillment_token: Optional[str] = None
    capabilities: Optional[AgentCapabilities] = None


class CheckoutSessionUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: Optional[List[ItemInput]] = None
    buyer_token: Optional[str] = None
    fulfillment_token: Optional[str] = None
    fulfillment_option_id: Optional[str] = None
    coupon_code: Optional[str] = None


class PaymentData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal["hyperswitch"]
    token: str
    billing_address: Optional[Address] = None
    approval_required: bool = False


class CheckoutSessionCompleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payment_data: PaymentData


class CancelSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: Optional[str] = None


AvailabilityStatus = Literal["in_stock", "out_of_stock", "low_stock", "preorder"]


class CheckoutItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    quantity: int
    title: Optional[str] = None
    image_url: Optional[str] = None
    availability_status: AvailabilityStatus = "in_stock"
    available_quantity: Optional[int] = None  # None = unlimited


class CheckoutLineItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    item: CheckoutItem
    base_amount: int = Field(ge=0)
    discount: int = Field(ge=0)
    subtotal: int = Field(ge=0)
    tax: int = Field(ge=0)
    total: int = Field(ge=0)
    gst_metadata: Optional[GSTMetadata] = None


TotalType = Literal[
    "items_base_amount",
    "items_discount",
    "subtotal",
    "discount",
    "fulfillment",
    "tax",
    "fee",
    "total",
]


class TotalsEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: TotalType
    display_text: str
    amount: int = Field(ge=0)


class FulfillmentOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["shipping", "pickup", "digital"]
    id: str
    title: str
    subtitle: str
    # shipping + pickup timing
    carrier: Optional[str] = None
    earliest_delivery_time: Optional[datetime] = None
    latest_delivery_time: Optional[datetime] = None
    # pickup-specific
    store_name: Optional[str] = None
    store_address: Optional[str] = None
    pickup_instructions: Optional[str] = None
    # digital-specific
    delivery_method: Optional[Literal["email", "download", "sms"]] = None
    # totals — same TotalsEntry pattern as CheckoutSession.totals
    totals: List["TotalsEntry"] = []


MessageSeverity = Literal["info", "low", "medium", "high", "critical"]
MessageContentType = Literal["plain", "markdown"]

WarningCode = Literal[
    "low_stock",
    "high_demand",
    "shipping_delay",
    "price_change",
    "expiring_promotion",
    "limited_availability",
    "discount_code_expired",
    "discount_code_invalid",
    "discount_code_combination_disallowed",
    "discount_code_minimum_not_met",
]

ErrorCode = Literal[
    "missing",
    "invalid",
    "out_of_stock",
    "payment_declined",
    "requires_sign_in",
    "requires_3ds",
    "quantity_exceeded",
    "coupon_invalid",
    "coupon_expired",
    "minimum_not_met",
    "maximum_exceeded",
    "region_restricted",
    "age_verification_required",
    "approval_required",
    "unsupported",
    "not_found",
    "conflict",
    "rate_limited",
    "expired",
    "intervention_required",
]


class InfoMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["info"] = "info"
    severity: MessageSeverity = "info"
    content_type: MessageContentType = "plain"
    content: str
    param: Optional[str] = None   # JSONPath of the field this message refers to


class WarningMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["warning"] = "warning"
    code: WarningCode
    severity: MessageSeverity = "low"
    content_type: MessageContentType = "plain"
    content: str
    param: Optional[str] = None


class ErrorMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["error"] = "error"
    code: ErrorCode
    severity: MessageSeverity = "high"
    content_type: MessageContentType = "plain"
    content: str
    param: Optional[str] = None


Message = Union[InfoMessage, WarningMessage, ErrorMessage]


DiscountStatus = Literal["applied", "rejected"]
DiscountType = Literal["percent", "flat"]
DiscountRejectionReason = Literal[
    "invalid",
    "expired",
    "minimum_not_met",
    "maximum_uses_exceeded",
    "not_combinable",
    "region_restricted",
]


class AppliedDiscount(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["applied"] = "applied"
    code: str
    type: DiscountType
    value: float           # e.g. 10 for 10% or 200 for ₹2 flat
    amount_saved: int      # paise saved by this discount


class RejectedDiscount(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["rejected"] = "rejected"
    code: str
    reason: DiscountRejectionReason


DiscountEntry = Union[AppliedDiscount, RejectedDiscount]


class Link(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal[
        "privacy_policy",
        "terms_of_use",
        "support",
        "return_policy",
        "refund_policy",
        "shipping_policy",
        "seller_shop_policies",
    ]
    url: str


SupportedPaymentMethod = Literal["card", "upi"]


class PaymentProvider(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal["hyperswitch"]
    supported_payment_methods: List[SupportedPaymentMethod]


CheckoutStatus = Literal[
    "not_ready_for_payment",
    "ready_for_payment",
    "authentication_required",
    "pending_approval",
    "complete_in_progress",   # payment submitted, async confirmation pending
    "completed",
    "requires_escalation",    # needs manual intervention (fraud hold, review)
    "canceled",
    "expired",
]


class CheckoutSession(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    status: CheckoutStatus
    currency: str = Field(min_length=3, max_length=3)
    locale: Optional[str] = None       # e.g. "hi-IN", "en-IN"
    timezone: Optional[str] = None     # e.g. "Asia/Kolkata"
    buyer_token: Optional[str] = None
    fulfillment_token: Optional[str] = None
    line_items: List[CheckoutLineItem]
    totals: List[TotalsEntry]
    fulfillment_options: List[FulfillmentOption]
    fulfillment_option_id: Optional[str] = None
    payment_provider: PaymentProvider
    messages: List[Message]
    discounts: List[DiscountEntry] = []
    links: List[Link]
    continue_url: Optional[str] = None  # web fallback URL if agent flow cannot complete
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    negotiated_capabilities: Optional[NegotiatedCapabilities] = None
    order: Optional[Dict[str, Any]] = None
    gst_metadata: Optional[GSTMetadata] = None
    cancel_reason: Optional[str] = None
    cancel_intent: Optional[Dict[str, Any]] = None  # snapshot of items+total at cancel time


class OrderSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    status: str
    checkout_session_id: str
    confirmation_number: str          # human-readable reference, e.g. "ORD-2026-XXXXX"
    total_amount: int                 # paise
    currency: str
    permalink_url: Optional[str] = None  # merchant-hosted order status page
    created_at: datetime
    updated_at: datetime


ErrorType = Literal["invalid_request", "not_found", "conflict", "server_error", "service_unavailable"]


class ErrorBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: ErrorType = "invalid_request"
    code: str
    message: str
    field: Optional[str] = None


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: ErrorBody
