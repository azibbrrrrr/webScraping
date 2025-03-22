import requests
import json
import psycopg2
import re
from dotenv import load_dotenv
import os
import googlemaps

# Load environment variables from .env
load_dotenv()

# PostgreSQL Database Config from .env
DB_CONFIG = {
    "dbname": os.getenv("DBNAME"),
    "user": os.getenv("USER"),
    "password": os.getenv("PASSWORD"),
    "host": os.getenv("HOST"),
    "port": os.getenv("PORT"),
}

# API Endpoint
URL = "https://www.mcdonalds.com.my/storefinder/index.php"

# Initialize Google Maps Client
gmaps = googlemaps.Client(key=os.getenv("GOOGLE_MAPS_API_KEY"))

# API Payload (Filters for Kuala Lumpur outlets)
PAYLOAD = {
    "ajax": 1,
    "action": "get_nearby_stores",
    "distance": 10000,
    "lat": "",
    "lng": "",
    "state": "",
    "products": "",
    "address": "kuala lumpur",
    "issuggestion": 0,
    "islocateus": 0
}

# Regex patterns
KL_ADDRESS_PATTERN = re.compile(r"\b\d{4,5}\b.*Kuala Lumpur", re.IGNORECASE)  # Matches KL addresses

def fetch_mcdonalds_data():
    """Fetch data from McDonald's API and return the parsed JSON response."""
    try:
        response = requests.post(URL, data=PAYLOAD, timeout=10)
        response.raise_for_status()
        return json.loads(response.content.decode("utf-8-sig"))  # Handle UTF-8 BOM
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        print(f"Error fetching data: {e}")
        return None

def geocode_address(address):
    """Retrieve latitude and longitude from an address using Google Maps API."""
    try:
        geocode_result = gmaps.geocode(address)
        if geocode_result:
            location = geocode_result[0]["geometry"]["location"]
            return location["lat"], location["lng"]
    except Exception as e:
        print(f"Geocoding error: {e}")
    return None, None

def filter_kl_stores(stores):
    """Filter and return only Kuala Lumpur outlets with a valid address."""
    return list(filter(lambda store: KL_ADDRESS_PATTERN.search(store.get("address", "")), stores))

def extract_store_details(store):
    name = store.get("name", "N/A")
    address = store.get("address", "N/A")
    city, state, country = "Kuala Lumpur", "Kuala Lumpur", "Malaysia"
    
    latitude, longitude = store.get("lat"), store.get("lng")

    # Part 2: Geocoding, retrieve outlets' geographical coordinates based on the stored address (if not available in the API response)
    if not latitude or not longitude:
        latitude, longitude = geocode_address(address)

    operating_hours = "24 Hours" if any(cat.get("cat_name") == "24 Hours" for cat in store.get("cat", [])) else "Not Available"
    waze_link = f"https://www.waze.com/live-map/directions?navigate=yes&to=ll.{latitude}%2C{longitude}" if latitude and longitude else ""

    return (name, address, city, state, country, latitude, longitude, operating_hours, waze_link)

def save_to_database(stores):
    """Save store data to PostgreSQL."""
    if not stores:
        print("No stores to save.")
        return

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # Ensure the table exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS mcdonalds_stores (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE,
                address TEXT UNIQUE,
                city TEXT,
                state TEXT,
                country TEXT,
                latitude DOUBLE PRECISION,
                longitude DOUBLE PRECISION,
                operating_hours TEXT,
                waze_link TEXT
            );
        """)

        insert_query = """
            INSERT INTO mcdonalds_stores (name, address, city, state, country, latitude, longitude, operating_hours, waze_link)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (name) DO NOTHING;  -- Avoid duplicate entries
        """

        data = [extract_store_details(store) for store in stores]
        cur.executemany(insert_query, data)

        conn.commit()
        print(f"✅ {len(data)} stores saved to database.")
        cur.close()
        conn.close()

    except psycopg2.Error as e:
        print(f"Database error: {e}")


if __name__ == "__main__":
    data = fetch_mcdonalds_data()
    if data and "stores" in data:
        kl_stores = filter_kl_stores(data["stores"])  # Apply KL filter
        save_to_database(kl_stores)  # Save only KL outlets
    else:
        print("Error: API response does not contain 'stores' key.")
