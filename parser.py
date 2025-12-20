import httpx
from typing import List
from schemas import CurrencyCreate


async def fetch_currency_rates() -> List[CurrencyCreate]:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get("https://www.cbr-xml-daily.ru/daily_json.js")
            response.raise_for_status()
            data = response.json()

            currencies = []
            for currency_code, currency_data in data["Valute"].items():
                currencies.append(CurrencyCreate(
                    code=currency_code,
                    name=currency_data["Name"],
                    value=currency_data["Value"],
                    previous=currency_data["Previous"],
                    nominal=currency_data["Nominal"]
                ))

            return currencies[:10]
    except Exception as e:
        print(f"Error fetching currency rates: {e}")
        return [
            CurrencyCreate(
                code="USD",
                name="Доллар США",
                value=90.50,
                previous=90.25,
                nominal=1
            ),
            CurrencyCreate(
                code="EUR",
                name="Евро",
                value=98.75,
                previous=98.50,
                nominal=1
            )
        ]