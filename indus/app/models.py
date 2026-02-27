from __future__ import annotations

import re
from typing import List, Optional, Dict, Any, Literal

from pydantic import BaseModel, Field, ConfigDict, EmailStr, field_validator


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


class Buyer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = None          # full name (for backward compatibility)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    account_type: Optional[str] = "guest"           # guest | registered | business
    authentication_status: Optional[str] = "unverified"  # unverified | verified | 3ds_authenticated


class ItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    quantity: int = Field(ge=1)


class PaymentHandlerDeclaration(BaseModel):
    """A payment handler the agent declares it can use."""
    model_config = ConfigDict(extra="allow")

    id: str                              # reverse-DNS: "com.hyperswitch.upi"
    version: str                         # "2026-02-24"
    psp: str                             # "hyperswitch"
    requires_delegate_payment: bool = True
    requires_pci_compliance: bool = False
    spec_uri: Optional[str] = None       # URI to the handler's machine-readable spec
    instrument_schema: Optional[Dict[str, Any]] = None  # JSON Schema for instrument params


class AgentCapabilities(BaseModel):
    """What this agent supports — sent in checkout create so the merchant can negotiate."""
    model_config = ConfigDict(extra="allow")

    payment_methods: List[str] = []      # ["card", "upi_collect", "upi_intent", "upi_qr"]
    payment_handlers: List[PaymentHandlerDeclaration] = []
    extensions: List[str] = []          # ["india_gst", "upi_vpa", "discounts"]
    locale: Optional[str] = None        # "hi-IN", "en-IN"
    timezone: Optional[str] = None      # "Asia/Kolkata"


class IndusCreateCheckoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    merchant_base_url: str
    items: List[ItemInput]
    buyer: Optional[Buyer] = None
    fulfillment_address: Optional[Address] = None
    capabilities: Optional[AgentCapabilities] = None


class IndusUpdateCheckoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: Optional[List[ItemInput]] = None
    buyer: Optional[Buyer] = None
    fulfillment_address: Optional[Address] = None
    fulfillment_option_id: Optional[str] = None


class IndusCheckoutResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    merchant_base_url: str
    checkout_session: Dict[str, Any]


class UPIData(BaseModel):
    model_config = ConfigDict(extra="allow")

    vpa: Optional[str] = None  # Virtual Payment Address for upi_collect


class PaymentIntentRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    amount: int = Field(ge=1)
    currency: str = Field(min_length=3, max_length=3)
    payment_method: Literal["card", "upi", "bank_redirect"]
    payment_method_type: Optional[str] = None
    payment_method_data: Optional[Dict[str, Any]] = None
    upi_data: Optional[UPIData] = None
    customer: Optional[Dict[str, Any]] = None
    return_url: Optional[str] = None
    confirm: bool = False
    metadata: Optional[Dict[str, Any]] = None


class PaymentIntentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payment_id: str
    client_secret: str
    status: str


class PaymentData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal["hyperswitch"]
    token: str
    billing_address: Optional[Address] = None


class CompleteCheckoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payment_data: PaymentData


class CompleteCheckoutResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: str
    status: str
    message: Optional[str] = None


class TokenRedeemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    purpose: Optional[str] = None


class TokenRedeemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str
    status: Literal["redeemed"]
    kind: Literal["buyer", "fulfillment"]
    payload: Dict[str, Any]
