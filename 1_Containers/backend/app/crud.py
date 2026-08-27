from sqlalchemy.orm import Session
from sqlalchemy import or_
from . import models, schemas
from typing import Optional
from datetime import datetime, timezone


def get_products(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
    category: Optional[str] = None,
    in_promo: Optional[bool] = None,
):
    query = db.query(models.Product)
    if search:
        query = query.filter(
            or_(
                models.Product.name.ilike(f"%{search}%"),
                models.Product.brand.ilike(f"%{search}%"),
            )
        )
    if category:
        query = query.filter(models.Product.category == category)
    if in_promo:
        query = query.filter(models.Product.is_in_promo.is_(True))

    total = query.count()
    items = query.order_by(models.Product.name).offset(skip).limit(limit).all()
    return items, total


def get_product(db: Session, product_id: int):
    return db.query(models.Product).filter(models.Product.id == product_id).first()


def update_product(db: Session, product_id: int, product: schemas.ProductUpdate):
    db_product = get_product(db, product_id)
    if not db_product:
        return None
    for key, value in product.model_dump(exclude_unset=True).items():
        setattr(db_product, key, value)
    db_product.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(db_product)
    return db_product


def delete_product(db: Session, product_id: int):
    db_product = get_product(db, product_id)
    if db_product:
        db.delete(db_product)
        db.commit()
    return db_product


def upsert_product(db: Session, product_data: dict):
    """Insert or update a product based on colruyt_id."""
    existing = (
        db.query(models.Product)
        .filter(models.Product.colruyt_id == product_data["colruyt_id"])
        .first()
    )

    now = datetime.now(timezone.utc)

    if existing:
        for key, value in product_data.items():
            if key != "colruyt_id":
                setattr(existing, key, value)
        existing.updated_at = now
        existing.last_scraped_at = now
        db.commit()
        db.refresh(existing)
        return existing, False
    else:
        product_data["last_scraped_at"] = now
        db_product = models.Product(**product_data)
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        return db_product, True


def get_categories(db: Session):
    return db.query(models.Product.category).distinct().all()


def create_scraper_run(db: Session):
    run = models.ScraperRun()
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def update_scraper_run(db: Session, run_id: int, **kwargs):
    run = db.query(models.ScraperRun).filter(models.ScraperRun.id == run_id).first()
    if run:
        for key, value in kwargs.items():
            setattr(run, key, value)
        db.commit()
        db.refresh(run)
    return run


def get_scraper_runs(db: Session, limit: int = 10):
    return (
        db.query(models.ScraperRun)
        .order_by(models.ScraperRun.started_at.desc())
        .limit(limit)
        .all()
    )


def get_latest_scraper_run(db: Session):
    return (
        db.query(models.ScraperRun)
        .order_by(models.ScraperRun.started_at.desc())
        .first()
    )
