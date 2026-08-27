import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routes import products, scraper

# Ensure app-level INFO logs (e.g. scraper progress) reach container output
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

Base.metadata.create_all(bind=engine)

# Lightweight migration: add columns introduced after the table was first created
with engine.begin() as _conn:
    _conn.exec_driver_sql(
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS quantity VARCHAR(100)"
    )

# Mark runs orphaned by a restart (in-memory thread is gone) as failed
from .database import SessionLocal
from . import models

with SessionLocal() as _db:
    _db.query(models.ScraperRun).filter(models.ScraperRun.status == "running").update(
        {"status": "failed", "error_message": "Interrupted by backend restart"}
    )
    _db.commit()

app = FastAPI(title="Colruyt Product Catalogue", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products.router, prefix="/api/products", tags=["products"])
app.include_router(scraper.router, prefix="/api/scraper", tags=["scraper"])


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
