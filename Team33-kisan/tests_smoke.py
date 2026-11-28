"""Quick smoke test: python tests_smoke.py  (needs internet + API key in .env)"""
import asyncio
from app.tools import get_weather, get_soil_health, get_market_prices
from app.agent import run_agent

async def main():
    print(await get_weather("Mandya"))
    print(await get_soil_health("Mandya"))
    print(await get_market_prices("Tomato", "Karnataka"))
    print(await run_agent("t1", "Should I irrigate my ragi today and where should I sell tomato?", "en", "Mandya"))
asyncio.run(main())
