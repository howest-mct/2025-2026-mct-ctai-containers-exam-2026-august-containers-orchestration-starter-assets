"""Flight Radar Check-in Simulator API."""

from __future__ import annotations

import asyncio
import json
import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from redis.asyncio import Redis


UTC = timezone.utc
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
TICK_TOKEN = os.getenv("SIMULATION_TICK_TOKEN", "dev-tick-token")
AUTO_TICK_SECONDS = int(os.getenv("AUTO_TICK_SECONDS", "0"))
CHECKIN_INTERVAL_SECONDS = int(os.getenv("CHECKIN_INTERVAL_SECONDS", "60"))


def generate_passengers(start_id: int, count: int) -> list[dict[str, str]]:
    """Create a deterministic, fictional manifest with one unique seat each."""
    first_names = ["Amina", "Mateo", "Sofia", "Luca", "Yuki", "Noor", "Arjun", "Amelie", "Diego", "Hana"]
    last_names = ["Khan", "Rossi", "Tanaka", "Silva", "Okafor", "Martinez"]
    seat_letters = "ABCDEF"
    passengers: list[dict[str, str]] = []
    for offset in range(count):
        seat_row, seat_index = divmod(offset, len(seat_letters))
        passengers.append(
            {
                "id": f"P{start_id + offset:03d}",
                "name": f"{first_names[offset % len(first_names)]} {last_names[(offset // len(first_names)) % len(last_names)]}",
                "seat": f"{seat_row + 1}{seat_letters[seat_index]}",
            }
        )
    return passengers


FLIGHTS: dict[str, dict[str, Any]] = {
    "SKY281": {
        "id": "SKY281",
        "number": "SKY 281",
        "origin": {"code": "BRU", "city": "Brussels", "name": "Brussels Airport"},
        "destination": {"code": "BCN", "city": "Barcelona", "name": "Barcelona-El Prat"},
        "aircraft": {"registration": "OO-FLY", "model": "Airbus A320neo", "capacity": 60},
        "scheduled_departure": "2026-08-24T10:30:00Z",
        "passengers": generate_passengers(1, 60),
    },
    "SKY492": {
        "id": "SKY492",
        "number": "SKY 492",
        "origin": {"code": "AMS", "city": "Amsterdam", "name": "Schiphol"},
        "destination": {"code": "CPH", "city": "Copenhagen", "name": "Kastrup"},
        "aircraft": {"registration": "PH-SKY", "model": "Embraer E190", "capacity": 60},
        "scheduled_departure": "2026-08-24T11:05:00Z",
        "passengers": generate_passengers(101, 60),
    },
}


class CheckInRequest(BaseModel):
    passenger_id: str


def utc_now() -> datetime:
    return datetime.now(UTC)


def iso_now() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def state_key(flight_id: str) -> str:
    return f"flight:{flight_id}:state"


def lock_key(flight_id: str) -> str:
    return f"flight:{flight_id}:checkin-lock"


def base_state(flight: dict[str, Any]) -> dict[str, Any]:
    next_tick = utc_now() + timedelta(seconds=CHECKIN_INTERVAL_SECONDS)
    return {
        "status": "Scheduled",
        "checked_in_ids": [],
        "events": [],
        "last_tick_at": None,
        "next_tick_at": next_tick.isoformat().replace("+00:00", "Z"),
        "version": 1,
    }


async def load_state(redis: Redis, flight: dict[str, Any]) -> dict[str, Any]:
    raw = await redis.get(state_key(flight["id"]))
    if raw is None:
        state = base_state(flight)
        await save_state(redis, flight["id"], state)
        return state
    return json.loads(raw)


async def save_state(redis: Redis, flight_id: str, value: dict[str, Any]) -> None:
    await redis.set(state_key(flight_id), json.dumps(value))


async def acquire_lock(redis: Redis, flight_id: str) -> str:
    token = secrets.token_urlsafe(18)
    locked = await redis.set(lock_key(flight_id), token, nx=True, ex=5)
    if not locked:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Another check-in is being processed; retry shortly.")
    return token


async def release_lock(redis: Redis, flight_id: str, token: str) -> None:
    await redis.eval(
        "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) end return 0",
        1,
        lock_key(flight_id),
        token,
    )


def flight_or_404(flight_id: str) -> dict[str, Any]:
    flight = FLIGHTS.get(flight_id.upper())
    if not flight:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flight not found.")
    return flight


def public_flight(flight: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    checked_in = len(state["checked_in_ids"])
    capacity = flight["aircraft"]["capacity"]
    return {
        "id": flight["id"],
        "number": flight["number"],
        "origin": flight["origin"],
        "destination": flight["destination"],
        "aircraft": flight["aircraft"],
        "scheduled_departure": flight["scheduled_departure"],
        "status": state["status"],
        "checked_in": checked_in,
        "capacity": capacity,
        "occupancy_percent": round((checked_in / capacity) * 100),
        "next_tick_at": state["next_tick_at"],
        "last_tick_at": state["last_tick_at"],
    }


def public_manifest(flight: dict[str, Any], state: dict[str, Any]) -> list[dict[str, Any]]:
    checked_ids = set(state["checked_in_ids"])
    return [{**passenger, "checked_in": passenger["id"] in checked_ids} for passenger in flight["passengers"]]


async def process_checkin(redis: Redis, flight: dict[str, Any], passenger_id: str, source: str) -> dict[str, Any]:
    token = await acquire_lock(redis, flight["id"])
    try:
        current = await load_state(redis, flight)
        passenger = next((item for item in flight["passengers"] if item["id"] == passenger_id.upper()), None)
        if passenger is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passenger is not on this flight.")
        if current["status"] in {"Departed", "Cancelled"}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Flight is already {current['status'].lower()}.")
        if passenger["id"] in current["checked_in_ids"]:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Passenger is already checked in.")
        current["checked_in_ids"].append(passenger["id"])
        current["events"].insert(0, {"at": iso_now(), "source": source, "passenger_id": passenger["id"], "passenger_name": passenger["name"], "seat": passenger["seat"]})
        if current["status"] == "Scheduled":
            current["status"] = "Boarding"
        if len(current["checked_in_ids"]) >= flight["aircraft"]["capacity"]:
            current["status"] = "Departed"
        if source == "automatic":
            current["last_tick_at"] = current["events"][0]["at"]
            current["next_tick_at"] = (utc_now() + timedelta(seconds=CHECKIN_INTERVAL_SECONDS)).isoformat().replace("+00:00", "Z")
        current["version"] += 1
        await save_state(redis, flight["id"], current)
        return {"flight": public_flight(flight, current), "event": current["events"][0]}
    finally:
        await release_lock(redis, flight["id"], token)


async def automatic_tick(redis: Redis, flight_id: str | None = None) -> dict[str, Any]:
    candidates = [flight_or_404(flight_id)] if flight_id else list(FLIGHTS.values())
    for flight in candidates:
        current = await load_state(redis, flight)
        if current["status"] in {"Departed", "Cancelled"}:
            continue
        next_passenger = next((p for p in flight["passengers"] if p["id"] not in current["checked_in_ids"]), None)
        if next_passenger is None:
            continue
        return await process_checkin(redis, flight, next_passenger["id"], "automatic")
    return {"message": "No eligible passenger was available for an automatic check-in."}


async def auto_tick_loop(app: FastAPI) -> None:
    while True:
        await asyncio.sleep(AUTO_TICK_SECONDS)
        try:
            await automatic_tick(app.state.redis)
        except Exception:
            # The application stays available if Redis is briefly restarting.
            pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis = Redis.from_url(REDIS_URL, decode_responses=True)
    await redis.ping()
    app.state.redis = redis
    task = asyncio.create_task(auto_tick_loop(app)) if AUTO_TICK_SECONDS > 0 else None
    try:
        yield
    finally:
        if task:
            task.cancel()
        await redis.aclose()


app = FastAPI(title="Flight Radar Check-in API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])


def redis_from(request: Request) -> Redis:
    return request.app.state.redis


@app.get("/health")
async def health(request: Request) -> dict[str, str]:
    await redis_from(request).ping()
    return {"status": "ok", "store": "redis"}


@app.get("/flights")
async def list_flights(request: Request) -> list[dict[str, Any]]:
    redis = redis_from(request)
    return [public_flight(flight, await load_state(redis, flight)) for flight in FLIGHTS.values()]


@app.get("/flights/{flight_id}")
async def get_flight(flight_id: str, request: Request) -> dict[str, Any]:
    flight = flight_or_404(flight_id)
    return public_flight(flight, await load_state(redis_from(request), flight))


@app.get("/flights/{flight_id}/manifest")
async def get_manifest(flight_id: str, request: Request) -> dict[str, Any]:
    flight = flight_or_404(flight_id)
    state = await load_state(redis_from(request), flight)
    return {"flight_id": flight["id"], "passengers": public_manifest(flight, state), "events": state["events"]}


@app.get("/simulation/state/{flight_id}")
async def get_simulation_state(flight_id: str, request: Request) -> dict[str, Any]:
    flight = flight_or_404(flight_id)
    state = await load_state(redis_from(request), flight)
    return {"flight": public_flight(flight, state), "events": state["events"]}


@app.post("/flights/{flight_id}/checkins", status_code=status.HTTP_201_CREATED)
async def manual_checkin(flight_id: str, payload: CheckInRequest, request: Request) -> dict[str, Any]:
    return await process_checkin(redis_from(request), flight_or_404(flight_id), payload.passenger_id, "manual")


@app.post("/simulation/tick")
async def simulation_tick(request: Request, x_simulation_token: str | None = Header(default=None)) -> dict[str, Any]:
    if not secrets.compare_digest(x_simulation_token or "", TICK_TOKEN):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid simulation token.")
    return await automatic_tick(redis_from(request))
