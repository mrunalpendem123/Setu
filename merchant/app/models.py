from __future__ import annotations

import re
from datetime import datetime
from typing import List, Optional, Dict, Any, Literal

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


class Buyer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None


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


class CheckoutItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    quantity: int
    title: Optional[str] = None
    image_url: Optional[str] = None


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

    type: Literal["shipping"]
    id: str
    title: str
    subtitle: str
    carrier: str
    earliest_delivery_time: datetime
    latest_delivery_time: datetime
    subtotal: int = Field(ge=0)
    tax: int = Field(ge=0)
    total: int = Field(ge=0)


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["info", "error"]
    content_type: Literal["text"]
    content: str
    param: Optional[str] = None
    code: Optional[str] = None


class Link(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["privacy_policy", "terms_of_use", "support"]
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
    "completed",
    "canceled",
    "expired",
]


class CheckoutSession(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    status: CheckoutStatus
    currency: str = Field(min_length=3, max_length=3)
    buyer_token: Optional[str] = None
    fulfillment_token: Optional[str] = None
    line_items: List[CheckoutLineItem]
    totals: List[TotalsEntry]
    fulfillment_options: List[FulfillmentOption]
    fulfillment_option_id: Optional[str] = None
    payment_provider: PaymentProvider
    messages: List[Message]
    links: List[Link]
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    negotiated_capabilities: Optional[NegotiatedCapabilities] = None
    order: Optional[Dict[str, Any]] = None
    gst_metadata: Optional[GSTMetadata] = None


class OrderSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    status: str
    created_at: datetime


class ErrorBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    field: Optional[str] = None


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: ErrorBody
