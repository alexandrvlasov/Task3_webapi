import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db import get_db
from parser import fetch_currency_rates
from models import Currency, CurrencyHistory
from nats_manager import nats_manager
from datetime import datetime

UPDATE_INTERVAL = 30


async def run_fetcher_once(db: AsyncSession):
    currencies = await fetch_currency_rates()

    print("Starting currency rates update")
    print(f"Received records: {len(currencies)}")
    added = 0
    updated = 0

    for item in currencies:
        stmt = select(Currency).where(Currency.code == item.code)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing is None:
            currency = Currency(
                code=item.code,
                name=item.name,
                value=item.value,
                previous=item.previous,
                nominal=item.nominal
            )
            db.add(currency)
            await db.commit()
            await db.refresh(currency)
            added += 1
            print(f"New currency: {currency.code} - {currency.name}")

            await nats_manager.publish_json(
                "currency.new",
                {
                    "code": currency.code,
                    "name": currency.name,
                    "value": currency.value,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            continue

        if existing.value != item.value:
            history = CurrencyHistory(
                currency_id=existing.id,
                value=existing.value,
                previous=existing.previous
            )
            db.add(history)
            old_value = existing.value
            existing.previous = existing.value
            existing.value = item.value
            existing.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(existing)
            updated += 1
            print(f"Currency rate changed: {existing.code} {old_value} -> {item.value}")

            await nats_manager.publish_json(
                "currency.updated",
                {
                    "code": existing.code,
                    "name": existing.name,
                    "old_value": old_value,
                    "new_value": existing.value,
                    "change": existing.value - old_value,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

    print(f"Completed. Added: {added}, updated: {updated}")


async def start_background_fetcher():
    print("Background currency fetcher started")
    while True:
        async for db in get_db():
            await run_fetcher_once(db)
        print(f"Next update in {UPDATE_INTERVAL} seconds...")
        await asyncio.sleep(UPDATE_INTERVAL)