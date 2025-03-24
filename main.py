import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from openai import OpenAI
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

# Load environment variables
load_dotenv()

# Supabase Transaction Pooler credentials
DB_USER = os.getenv("user")
DB_PASSWORD = os.getenv("password")
DB_HOST = os.getenv("host")
DB_PORT = os.getenv("port")
DB_NAME = os.getenv("dbname")

# OpenAI API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Initialize FastAPI
app = FastAPI()

# Function to get a database connection (Transaction Pooler)
def get_db_connection():
    try:
        return psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            cursor_factory=RealDictCursor  # Return query results as dictionaries
        )
    except Exception as e:
        logging.error(f"Error connecting to the database: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed.")

@app.get("/outlets", tags=["Outlets"])
def get_outlets(city: str = Query(None), name: str = Query(None)):
    """Fetch all McDonald's outlets with optional filtering by city or name."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

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
            conditions.append("s.city ILIKE %s")
            params.append(f"%{city}%")
        if name:
            conditions.append("s.name ILIKE %s")
            params.append(f"%{name}%")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " GROUP BY s.id"

        cursor.execute(query, tuple(params))
        outlets = cursor.fetchall()

        cursor.close()
        conn.close()  # Close connection after each request (Supabase handles pooling)

        return outlets

    except Exception as e:
        logging.error(f"Database error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Database error occurred", "detail": str(e)}
        )

@app.get("/outlets/{outlet_id}", tags=["Outlets"])
def get_outlet(outlet_id: int):
    """Fetch a single outlet by its ID."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            SELECT s.id, s.name, s.address, s.city, s.state, s.country, 
                   s.latitude, s.longitude, s.operating_hours, s.waze_link,
                   ARRAY_AGG(f.name) AS features
            FROM mcdonalds_stores s
            LEFT JOIN outlet_features of ON s.id = of.outlet_id
            LEFT JOIN features f ON of.feature_id = f.id
            WHERE s.id = %s
            GROUP BY s.id
        """
        
        cursor.execute(query, (outlet_id,))
        outlet = cursor.fetchone()

        cursor.close()
        conn.close()

        if outlet:
            return outlet
        raise HTTPException(status_code=404, detail="Outlet not found")

    except Exception as e:
        logging.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred.")

@app.get("/search")
def search_outlets(query: str = Query(..., description="Enter your query")):
    """Search outlets based on a natural language query."""
    feature_ids = extract_features_llm(query)
    outlets = get_outlets_by_features(feature_ids)
    return {"query": query, "results": outlets}

def get_outlets_by_features(feature_ids):
    """Fetch McDonald's outlets matching extracted feature IDs, including features list."""
    if not feature_ids:
        return []

    query = """
        WITH matched_outlets AS (
            SELECT s.id
            FROM mcdonalds_stores s
            JOIN outlet_features of ON s.id = of.outlet_id
            WHERE of.feature_id = ANY(%s)
            GROUP BY s.id
            HAVING COUNT(DISTINCT of.feature_id) = %s
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
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(query, (feature_ids, len(feature_ids)))
        results = cursor.fetchall()

        cursor.close()
        conn.close()

        return results

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
# uvicorn main:app --reload
