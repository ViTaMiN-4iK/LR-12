from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RoleEnum(str, Enum):
    customer = "customer"
    courier = "courier"
    admin = "admin"


class OrderStatusEnum(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    preparing = "preparing"
    ready_for_pickup = "ready_for_pickup"
    out_for_delivery = "out_for_delivery"
    delivered = "delivered"
    cancelled = "cancelled"


# --- Auth ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: RoleEnum
    is_active: bool
    created_at: datetime | None = None


# --- Restaurant ---
class RestaurantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    address: str = Field(min_length=1, max_length=500)
    is_open: bool = True


class RestaurantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    address: str | None = Field(default=None, min_length=1, max_length=500)
    is_open: bool | None = None


class RestaurantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    address: str
    is_open: bool
    created_at: datetime | None = None


# --- Dish ---
class DishCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    price: Decimal = Field(ge=0)
    is_available: bool = True

    @field_validator("price")
    @classmethod
    def price_two_decimals(cls, v: Decimal) -> Decimal:
        return v.quantize(Decimal("0.01"))


class DishUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    price: Decimal | None = Field(default=None, ge=0)
    is_available: bool | None = None


class DishOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    restaurant_id: int
    name: str
    description: str | None
    price: Decimal
    is_available: bool


# --- Courier ---
class CourierCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    vehicle_info: str = Field(default="", max_length=255)


class CourierUpdate(BaseModel):
    vehicle_info: str | None = Field(default=None, max_length=255)
    is_available: bool | None = None


class CourierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    vehicle_info: str
    is_available: bool
    user: UserOut


# --- Order ---
class OrderItemIn(BaseModel):
    dish_id: int
    quantity: int = Field(ge=1, le=99)


class OrderCreate(BaseModel):
    restaurant_id: int
    items: list[OrderItemIn] = Field(min_length=1)

    @field_validator("items")
    @classmethod
    def unique_dishes(cls, items: list[OrderItemIn]) -> list[OrderItemIn]:
        ids = [i.dish_id for i in items]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate dish_id in one order is not allowed; merge quantities client-side")
        return items


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dish_id: int
    quantity: int
    unit_price: Decimal


class OrderTrackingEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: OrderStatusEnum
    location_note: str | None
    created_at: datetime | None


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    restaurant_id: int
    courier_id: int | None
    status: OrderStatusEnum
    total_amount: Decimal
    created_at: datetime | None
    delivered_at: datetime | None
    items: list[OrderItemOut] = []
    events: list[OrderTrackingEventOut] = []


class OrderStatusUpdate(BaseModel):
    status: OrderStatusEnum
    location_note: str | None = Field(default=None, max_length=500)


class AssignCourierBody(BaseModel):
    courier_profile_id: int


# --- Reports ---
class TopDishRow(BaseModel):
    dish_id: int
    dish_name: str
    restaurant_id: int
    restaurant_name: str
    units_sold: int
    revenue: Decimal


class CourierLoadRow(BaseModel):
    courier_profile_id: int
    courier_name: str
    orders_delivered: int
    total_revenue: Decimal
