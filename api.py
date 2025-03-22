from fastapi import FastAPI, HTTPException, Query
import asyncpg
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database config
DB_CONFIG = {
    "database": os.getenv("DBNAME"), 
    "user": os.getenv("USER"),
    "password": os.getenv("PASSWORD"),
    "host": os.getenv("HOST"),
    "port": os.getenv("PORT"),
}

# Initialize FastAPI
app = FastAPI()

async def connect_db():
    """Establish a connection to PostgreSQL."""
    return await asyncpg.connect(**DB_CONFIG)

@app.get("/outlets", tags=["Outlets"])
async def get_outlets(city: str = Query(None, description="Filter by city"), name: str = Query(None, description="Filter by outlet name")):
    """Fetch all outlets, with optional filtering by city or name."""
    try:
        conn = await connect_db()
        query = "SELECT id, name, address, city, state, country, latitude, longitude, operating_hours, waze_link FROM mcdonalds_stores"
        conditions = []
        params = []

        if city:
            conditions.append("city ILIKE $1")
            params.append(f"%{city}%")
        if name:
            conditions.append("name ILIKE $" + str(len(params) + 1))
            params.append(f"%{name}%")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        outlets = await conn.fetch(query, *params)
        await conn.close()

        return [{"id": o["id"], "name": o["name"], "address": o["address"], "city": o["city"], 
                 "state": o["state"], "country": o["country"], "latitude": o["latitude"], 
                 "longitude": o["longitude"], "operating_hours": o["operating_hours"], 
                 "waze_link": o["waze_link"]} for o in outlets]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@app.get("/outlets/{outlet_id}", tags=["Outlets"])
async def get_outlet(outlet_id: int):
    """Fetch a single outlet by its ID."""
    try:
        conn = await connect_db()
        outlet = await conn.fetchrow("SELECT * FROM mcdonalds_stores WHERE id = $1", outlet_id)
        await conn.close()

        if outlet:
            return dict(outlet)
        else:
            raise HTTPException(status_code=404, detail="Outlet not found")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

