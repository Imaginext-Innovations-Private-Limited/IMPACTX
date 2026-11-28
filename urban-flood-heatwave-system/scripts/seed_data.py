"""
Seed script — populates the database with sample flood zones and cooling centres for Mumbai.
Run once after the first startup:
  cd backend && python scripts/seed_data.py
"""

import asyncio
import sys
sys.path.insert(0, '.')

from app.core.database import init_db, AsyncSessionLocal
from app.models.flood_zone import FloodZone
from app.models.cooling_center import CoolingCenter


FLOOD_ZONES = [
    FloodZone(zone_id='mum-dharavi',  name='Dharavi',  city='Mumbai', latitude=19.040, longitude=72.854, drainage_capacity_mm=20, lake_level_pct=85, elevation_m=3),
    FloodZone(zone_id='mum-kurla',    name='Kurla',    city='Mumbai', latitude=19.072, longitude=72.880, drainage_capacity_mm=25, lake_level_pct=70, elevation_m=5),
    FloodZone(zone_id='mum-andheri',  name='Andheri',  city='Mumbai', latitude=19.113, longitude=72.868, drainage_capacity_mm=30, lake_level_pct=65, elevation_m=8),
    FloodZone(zone_id='mum-worli',    name='Worli',    city='Mumbai', latitude=19.017, longitude=72.816, drainage_capacity_mm=35, lake_level_pct=50, elevation_m=12),
    FloodZone(zone_id='mum-bandra',   name='Bandra',   city='Mumbai', latitude=19.054, longitude=72.841, drainage_capacity_mm=40, lake_level_pct=45, elevation_m=15),
    FloodZone(zone_id='mum-dadar',    name='Dadar',    city='Mumbai', latitude=19.018, longitude=72.843, drainage_capacity_mm=28, lake_level_pct=72, elevation_m=6),
    FloodZone(zone_id='mum-colaba',   name='Colaba',   city='Mumbai', latitude=18.907, longitude=72.814, drainage_capacity_mm=22, lake_level_pct=60, elevation_m=2),
]

COOLING_CENTRES = [
    CoolingCenter(name='BKC Community Hall', center_type='Community Hall', city='Mumbai', address='Bandra Kurla Complex, Mumbai 400051', latitude=19.065, longitude=72.869, capacity=500, has_water=True, has_medical=True, phone='022-1234-5678'),
    CoolingCenter(name='Dharavi School No. 7', center_type='School', city='Mumbai', address='90 Feet Road, Dharavi, Mumbai 400017', latitude=19.038, longitude=72.851, capacity=300, has_water=True, has_medical=False, phone='022-9876-5432'),
    CoolingCenter(name='Sion Hospital OPD Hall', center_type='Hospital', city='Mumbai', address='Sion Hospital Rd, Mumbai 400022', latitude=19.040, longitude=72.863, capacity=200, has_water=True, has_medical=True, phone='022-2222-3333'),
    CoolingCenter(name='Andheri Sports Complex', center_type='Sports Complex', city='Mumbai', address='MHADA Colony, Andheri West, Mumbai 400053', latitude=19.117, longitude=72.843, capacity=400, has_water=True, has_medical=False, phone='022-4444-5555'),
    CoolingCenter(name='Worli Community Centre', center_type='Community Hall', city='Mumbai', address='Worli Naka, Mumbai 400018', latitude=19.019, longitude=72.820, capacity=250, has_water=True, has_medical=False, phone='022-6666-7777'),
]


async def seed():
    await init_db()
    async with AsyncSessionLocal() as db:
        for zone in FLOOD_ZONES:
            db.add(zone)
        for centre in COOLING_CENTRES:
            db.add(centre)
        await db.commit()
    print(f"✅ Seeded {len(FLOOD_ZONES)} flood zones and {len(COOLING_CENTRES)} cooling centres.")


if __name__ == '__main__':
    asyncio.run(seed())
