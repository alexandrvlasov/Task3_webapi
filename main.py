from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
import asyncio
from datetime import datetime

from db import init_db, get_db
from models import Currency, CurrencyHistory
from schemas import CurrencyCreate, CurrencyRead, CurrencyUpdate, CurrencyHistoryRead
from currency_fetcher import start_background_fetcher, run_fetcher_once
from nats_listener import start_nats_listener
from ws_manager import ConnectionManager
from nats_manager import nats_manager

app = FastAPI(
    title="Currency Rates API",
    version="1.0.0",
    description="REST API for currency rates with WebSocket and NATS"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

manager = ConnectionManager()


@app.websocket("/ws/currencies")
async def ws_currencies(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.handle(data, websocket)
    except WebSocketDisconnect:
        await manager.disconnect(websocket)


@app.on_event("startup")
async def on_startup():
    await init_db()
    asyncio.create_task(start_nats_listener(manager))
    asyncio.create_task(start_background_fetcher())
    print("Application started")


@app.get("/")
async def root():
    return {
        "message": "Currency Rates API",
        "endpoints": {
            "REST API": {
                "GET /currencies": "List all currencies",
                "GET /currencies/{code}": "Get currency by code",
                "POST /currencies": "Create currency",
                "PATCH /currencies/{code}": "Update currency",
                "DELETE /currencies/{code}": "Delete currency",
                "GET /history/{currency_id}": "Get currency history",
                "POST /tasks/run": "Force update currencies"
            },
            "WebSocket": {
                "WS /ws/currencies": "Real-time notifications"
            }
        }
    }


@app.get("/currencies", response_model=list[CurrencyRead])
async def list_currencies(db: AsyncSession = Depends(get_db)):
    stmt = select(Currency).order_by(Currency.code)
    result = await db.execute(stmt)
    currencies = result.scalars().all()
    return currencies


@app.get("/currencies/{currency_code}", response_model=CurrencyRead)
async def get_currency(currency_code: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Currency).where(Currency.code == currency_code.upper())
    result = await db.execute(stmt)
    currency = result.scalar_one_or_none()
    if currency is None:
        raise HTTPException(status_code=404, detail="Currency not found")
    return currency


@app.post("/currencies", response_model=CurrencyRead, status_code=201)
async def create_currency(payload: CurrencyCreate, db: AsyncSession = Depends(get_db)):
    stmt = select(Currency).where(Currency.code == payload.code.upper())
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Currency with this code already exists")

    currency = Currency(**payload.dict())
    db.add(currency)
    await db.commit()
    await db.refresh(currency)

    await nats_manager.publish_json(
        "currency.new",
        {
            "code": currency.code,
            "name": currency.name,
            "value": currency.value,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    print(f"Published to NATS: currency.new for {currency.code}")

    return currency


@app.patch("/currencies/{currency_code}", response_model=CurrencyRead)
async def update_currency(currency_code: str, payload: CurrencyUpdate, db: AsyncSession = Depends(get_db)):
    stmt = select(Currency).where(Currency.code == currency_code.upper())
    result = await db.execute(stmt)
    currency = result.scalar_one_or_none()
    if currency is None:
        raise HTTPException(status_code=404, detail="Currency not found")

    update_data = payload.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == "value" and value != currency.value:
            currency.previous = currency.value
        setattr(currency, field, value)

    await db.commit()
    await db.refresh(currency)

    if "value" in update_data and update_data["value"] != currency.value:
        await nats_manager.publish_json(
            "currency.updated",
            {
                "code": currency.code,
                "name": currency.name,
                "old_value": currency.previous,
                "new_value": currency.value,
                "change": currency.value - currency.previous,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        print(f"Published to NATS: currency.updated for {currency.code}")

    return currency


@app.delete("/currencies/{currency_code}", status_code=204)
async def delete_currency(currency_code: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Currency).where(Currency.code == currency_code.upper())
    result = await db.execute(stmt)
    currency = result.scalar_one_or_none()
    if currency is None:
        raise HTTPException(status_code=404, detail="Currency not found")

    await db.delete(currency)
    await db.commit()

    await nats_manager.publish_json(
        "currency.deleted",
        {
            "code": currency.code,
            "name": currency.name,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    print(f"Published to NATS: currency.deleted for {currency.code}")


@app.get("/history/{currency_id}", response_model=list[CurrencyHistoryRead])
async def get_currency_history(currency_id: int, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(CurrencyHistory)
        .where(CurrencyHistory.currency_id == currency_id)
        .order_by(CurrencyHistory.checked_at)
    )
    result = await db.execute(stmt)
    history = result.scalars().all()
    return history


@app.post("/tasks/run")
async def force_run(background_tasks: BackgroundTasks):
    async def run_task():
        async for db in get_db():
            await run_fetcher_once(db)

    background_tasks.add_task(run_task)
    return {"status": "Currency update started in background"}
