from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Text
from sqlalchemy.sql import func
from .database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    colruyt_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(500), nullable=False)
    brand = Column(String(255))
    price = Column(Numeric(10, 2))
    price_per_unit = Column(Numeric(10, 2))
    unit = Column(String(50))
    quantity = Column(String(100))
    category = Column(String(255), index=True)
    subcategory = Column(String(255))
    image_url = Column(String(1000))
    url = Column(String(1000))
    is_in_promo = Column(Boolean, default=False)
    promo_price = Column(Numeric(10, 2))
    description = Column(Text)
    last_scraped_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ScraperRun(Base):
    __tablename__ = "scraper_runs"

    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True))
    status = Column(String(50), default="running")  # running, completed, failed
    products_scraped = Column(Integer, default=0)
    products_new = Column(Integer, default=0)
    products_updated = Column(Integer, default=0)
    error_message = Column(Text)
