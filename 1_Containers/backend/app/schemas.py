from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal


class ProductBase(BaseModel):
    name: str
    brand: Optional[str] = None
    price: Optional[Decimal] = None
    price_per_unit: Optional[Decimal] = None
    unit: Optional[str] = None
    quantity: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    image_url: Optional[str] = None
    url: Optional[str] = None
    is_in_promo: Optional[bool] = False
    promo_price: Optional[Decimal] = None
    description: Optional[str] = None


class ProductCreate(ProductBase):
    colruyt_id: str


class ProductUpdate(ProductBase):
    name: Optional[str] = None


class ProductResponse(ProductBase):
    id: int
    colruyt_id: str
    last_scraped_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    page: int
    size: int


class ScraperRunResponse(BaseModel):
    id: int
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    status: str
    products_scraped: int
    products_new: int
    products_updated: int
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}
