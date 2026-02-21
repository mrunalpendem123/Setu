from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Dict, Any, Literal

from pydantic import BaseModel, Field, EmailStr, ConfigDict


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


class Buyer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None


class ItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    quantity: int = Field(ge=1)


class CheckoutSessionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: List[ItemInput]
    buyer: Optional[Buyer] = None
    fulfillment_address: Optional[Address] = None


class CheckoutSessionUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: Optional[List[ItemInput]] = None
    buyer: Optional[Buyer] = None
    fulfillment_address: Optional[Address] = None
    fulfillment_option_id: Optional[str] = None


class PaymentData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal["hyperswitch"]
    token: str
    billing_address: Optional[Address] = None


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
    "completed",
    "canceled",
]


class CheckoutSession(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    status: CheckoutStatus
    currency: str = Field(min_length=3, max_length=3)
    buyer: Optional[Buyer] = None
    fulfillment_address: Optional[Address] = None
    line_items: List[CheckoutLineItem]
    totals: List[TotalsEntry]
    fulfillment_options: List[FulfillmentOption]
    fulfillment_option_id: Optional[str] = None
    payment_provider: PaymentProvider
    messages: List[Message]
    links: List[Link]
    created_at: datetime
    updated_at: datetime
    order: Optional[Dict[str, Any]] = None


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
