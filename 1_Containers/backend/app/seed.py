"""Seed the product catalogue from a bundled JSON snapshot.

Ensures the app has data even when the scraper is blocked or fails (e.g. during
an exam). The seed is only applied when the products table is empty, so a real
scrape always takes precedence.

Regenerate the snapshot from a populated database with:
    python -m app.seed export          # export everything
    python -m app.seed export 2000     # export at most 2000 products
"""

import json
import logging
import pathlib
from decimal import Decimal

from sqlalchemy.orm import Session

from . import models
from .database import SessionLocal

logger = logging.getLogger("app.seed")

SEED_FILE = pathlib.Path(__file__).parent / "seed_data" / "products.json"

# Columns persisted in the seed (skips DB-managed id/timestamps)
_FIELDS = [
    "colruyt_id", "name", "brand", "price", "price_per_unit", "unit", "quantity",
    "category", "subcategory", "image_url", "url", "is_in_promo", "promo_price",
    "description",
]


def seed_if_empty(db: Session) -> None:
    """Load the bundled snapshot into an empty products table."""
    if db.query(models.Product).count() > 0:
        return
    if not SEED_FILE.exists():
        logger.warning("No seed file found — catalogue starts empty")
        return

    rows = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    for row in rows:
        db.add(models.Product(**{k: row.get(k) for k in _FIELDS}))
    db.commit()
    logger.info(f"Seeded {len(rows)} products from bundled snapshot")


def count_seed() -> int:
    """Number of products available in the bundled snapshot (0 if none)."""
    if not SEED_FILE.exists():
        return 0
    try:
        return len(json.loads(SEED_FILE.read_text(encoding="utf-8")))
    except (ValueError, OSError):
        return 0


def load_seed(db: Session) -> int:
    """Insert the bundled snapshot and return how many products were added."""
    rows = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    for row in rows:
        db.add(models.Product(**{k: row.get(k) for k in _FIELDS}))
    db.commit()
    return len(rows)


def export(limit: int | None = None) -> None:
    """Dump the current catalogue to the seed file (for regenerating the snapshot)."""
    db = SessionLocal()
    try:
        query = db.query(models.Product).order_by(
            models.Product.category, models.Product.name
        )
        if limit:
            query = query.limit(limit)

        rows = []
        for product in query.all():
            row = {}
            for field in _FIELDS:
                value = getattr(product, field)
                row[field] = float(value) if isinstance(value, Decimal) else value
            rows.append(row)

        SEED_FILE.parent.mkdir(parents=True, exist_ok=True)
        SEED_FILE.write_text(
            json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        print(f"Exported {len(rows)} products to {SEED_FILE}")
    finally:
        db.close()


if __name__ == "__main__":
    import sys

    n = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[1] == "export" else None
    export(n)
