import os
import asyncpg
from openai import OpenAI
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize OpenAI client
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)

# Database config
DB_CONFIG = {
    "database": os.getenv("DBNAME"), 
    "user": os.getenv("USER"),
    "password": os.getenv("PASSWORD"),
    "host": os.getenv("HOST"),
    "port": os.getenv("PORT"),
}

DATABASE_URL = os.getenv("DATABASE_URL")

# Initialize FastAPI
app = FastAPI()

async def get_db_connection():
    """Create a new database connection."""
    return await asyncpg.connect(DATABASE_URL)

@app.get("/outlets", tags=["Outlets"])
async def get_outlets(city: str = Query(None, description="Filter by city"), name: str = Query(None, description="Filter by outlet name")):
    """Fetch all outlets, including features, with optional filtering by city or name."""
    try:
        conn = await get_db_connection()
        query = """
            SELECT s.id, s.name, s.address, s.city, s.state, s.country, 
                   s.latitude, s.longitude, s.operating_hours, s.waze_link,
                   ARRAY_AGG(f.name) AS features
            FROM mcdonalds_stores s
            LEFT JOIN outlet_features of ON s.id = of.outlet_id
            LEFT JOIN features f ON of.feature_id = f.id
        """
        conditions = []
        params = []

        if city:
            conditions.append(f"s.city ILIKE ${len(params) + 1}")
            params.append(f"%{city}%")
        if name:
            conditions.append(f"s.name ILIKE ${len(params) + 1}")
            params.append(f"%{name}%")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " GROUP BY s.id"

        outlets = await conn.fetch(query, *params)
        await conn.close()

        return [{"id": o["id"], "name": o["name"], "address": o["address"], "city": o["city"], 
                 "state": o["state"], "country": o["country"], "latitude": o["latitude"], 
                 "longitude": o["longitude"], "operating_hours": o["operating_hours"], 
                 "waze_link": o["waze_link"], "features": o["features"]} for o in outlets]

    except Exception as e:
        logging.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred.")



@app.get("/outlets/{outlet_id}", tags=["Outlets"])
async def get_outlet(outlet_id: int):
    """Fetch a single outlet by its ID."""
    try:
        conn = await get_db_connection()
        outlet = await conn.fetchrow("SELECT * FROM mcdonalds_stores WHERE id = $1", outlet_id)
        await conn.close()
        if outlet:
            return dict(outlet)
        raise HTTPException(status_code=404, detail="Outlet not found")

    except Exception as e:
        logging.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred.")

@app.get("/search")
async def search_outlets(query: str = Query(..., description="Enter your query")):
    """Search outlets based on a natural language query."""
    feature_ids = extract_features_llm(query)
    outlets = await get_outlets_by_features(feature_ids)
    return {"query": query, "results": outlets}

async def get_outlets_by_features(feature_ids):
    """Fetch McDonald's outlets matching extracted feature IDs, including features list."""
    if not feature_ids:
        return []

    query = """
        WITH matched_outlets AS (
            SELECT s.id
            FROM mcdonalds_stores s
            JOIN outlet_features of ON s.id = of.outlet_id
            WHERE of.feature_id = ANY($1)
            GROUP BY s.id
            HAVING COUNT(DISTINCT of.feature_id) = $2
        )
        SELECT s.id, s.name, s.address, s.city, s.state, s.country, 
               s.latitude, s.longitude, s.operating_hours, s.waze_link,
               ARRAY_AGG(DISTINCT f.name) AS features
        FROM mcdonalds_stores s
        JOIN outlet_features of ON s.id = of.outlet_id
        JOIN features f ON of.feature_id = f.id
        WHERE s.id IN (SELECT id FROM matched_outlets)
        GROUP BY s.id;
    """

    try:
        conn = await get_db_connection()
        results = await conn.fetch(query, feature_ids, len(feature_ids))
        await conn.close()
        
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "address": row["address"],
                "city": row["city"],
                "state": row["state"],
                "country": row["country"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "operating_hours": row["operating_hours"],
                "waze_link": row["waze_link"],
                "features": row["features"],
            }
            for row in results
        ]

    except Exception as e:
        logging.error(f"Database query error: {e}")
        return []

FEATURES = {
    "24 Hours": 1,
    "Birthday Party": 2,
    "Breakfast": 3,
    "Cashless Facility": 4,
    "Dessert Center": 5,
    "Digital Order Kiosk": 6,
    "McCafe": 7,
    "WiFi": 8,
    "McDelivery": 9,
    "Drive-Thru": 62,
    "Electric Vehicle": 321,
    "Surau": 322,
}

def extract_features_llm(query):
    """Uses LLM to extract relevant McDonald's features from user query."""
    prompt = f"""
    Extract relevant McDonald's outlet features from the following query:
    
    Query: "{query}"
    
    Features: {list(FEATURES.keys())}
    
    Return only feature names from the list, separated by commas.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Extract features from queries based on a predefined list."},
                {"role": "user", "content": prompt}
            ]
        )

        extracted_text = response.choices[0].message.content.strip()
        feature_names = [f.strip() for f in extracted_text.split(",") if f.strip() in FEATURES]

        return [FEATURES[name] for name in feature_names]

    except Exception as e:
        logging.error(f"LLM error: {e}")
        return []

# To run the API, execute:
# uvicorn api:app --reload
