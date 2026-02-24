from __future__ import annotations

from typing import List, Optional, Dict, Any, Literal

from pydantic import BaseModel, Field, ConfigDict, EmailStr


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


class IndusCreateCheckoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    merchant_base_url: str
    items: List[ItemInput]
    buyer: Optional[Buyer] = None
    fulfillment_address: Optional[Address] = None


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


class PaymentIntentRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    amount: int = Field(ge=1)
    currency: str = Field(min_length=3, max_length=3)
    payment_method: Literal["card", "upi"]
    payment_method_type: Optional[str] = None
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
