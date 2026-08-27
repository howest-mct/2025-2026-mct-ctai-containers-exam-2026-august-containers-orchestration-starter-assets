import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from .. import crud, schemas
from ..database import get_db, SessionLocal
from ..scraper import log_buffer

# Log under the app.scraper hierarchy so messages appear in the live log buffer
logger = logging.getLogger("app.scraper.runner")
router = APIRouter()

log_buffer.setup()

_executor = ThreadPoolExecutor(max_workers=1)
_scraper_running = False


@router.post("/run")
async def trigger_scraper(db: Session = Depends(get_db)):
    global _scraper_running
    if _scraper_running:
        raise HTTPException(status_code=409, detail="Scraper is already running")

    run = crud.create_scraper_run(db)
    _scraper_running = True

    loop = asyncio.get_event_loop()
    loop.run_in_executor(_executor, _run_scraper_in_thread, run.id)

    return {"message": "Scraper started", "run_id": run.id}


def _run_scraper_in_thread(run_id: int):
    global _scraper_running
    db = SessionLocal()
    try:
        from ..scraper.colruyt import run_scraper_sync
        run_scraper_sync(run_id, db)
    except Exception as e:
        logger.error(f"Scraper thread error: {e}")
        crud.update_scraper_run(db, run_id, status="failed", error_message=str(e))
    finally:
        _scraper_running = False
        db.close()


@router.get("/status")
def get_status(db: Session = Depends(get_db)):
    run = crud.get_latest_scraper_run(db)
    return {
        "is_running": _scraper_running,
        "latest_run": schemas.ScraperRunResponse.model_validate(run) if run else None,
    }


@router.get("/history", response_model=list[schemas.ScraperRunResponse])
def get_history(db: Session = Depends(get_db)):
    return crud.get_scraper_runs(db)


@router.get("/logs")
def get_logs(after: int = Query(0, ge=0)):
    return {"lines": log_buffer.get_logs(after)}
