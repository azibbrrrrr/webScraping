import asyncio
from main import get_outlets_by_features

async def run_test():
    feature_ids = [8, 62]  # WiFi and Drive-Thru
    outlets = await get_outlets_by_features(feature_ids)
    
    outlet_ids = [outlet["id"] for outlet in outlets]  # Extract only the IDs
    print(f"Feature IDs: {feature_ids}")
    print(f"Outlet IDs: {outlet_ids}")

if __name__ == "__main__":
    asyncio.run(run_test())
