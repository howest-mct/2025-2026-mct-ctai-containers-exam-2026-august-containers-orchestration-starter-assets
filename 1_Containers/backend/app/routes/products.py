from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from .. import crud, schemas, seed
from ..database import get_db

router = APIRouter()


@router.get("", response_model=schemas.ProductListResponse)
def list_products(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    category: Optional[str] = None,
    in_promo: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    skip = (page - 1) * size
    items, total = crud.get_products(
        db, skip=skip, limit=size, search=search, category=category, in_promo=in_promo
    )
    return {"items": items, "total": total, "page": page, "size": size}


@router.get("/categories")
def list_categories(db: Session = Depends(get_db)):
    rows = crud.get_categories(db)
    return [r[0] for r in rows if r[0]]


@router.get("/seed/info")
def seed_info(db: Session = Depends(get_db)):
    _, total = crud.get_products(db, limit=1)
    return {"available": seed.count_seed(), "product_count": total}


@router.post("/seed")
def load_sample_data(db: Session = Depends(get_db)):
    _, total = crud.get_products(db, limit=1)
    if total > 0:
        raise HTTPException(status_code=409, detail="Catalogue is not empty")
    if seed.count_seed() == 0:
        raise HTTPException(status_code=404, detail="No seed data available")
    loaded = seed.load_seed(db)
    return {"loaded": loaded}


@router.get("/{product_id}", response_model=schemas.ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = crud.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.put("/{product_id}", response_model=schemas.ProductResponse)
def update_product(
    product_id: int,
    product: schemas.ProductUpdate,
    db: Session = Depends(get_db),
):
    updated = crud.update_product(db, product_id, product)
    if not updated:
        raise HTTPException(status_code=404, detail="Product not found")
    return updated


@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_product(db, product_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted"}
