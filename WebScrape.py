import requests
import json
import psycopg2
import re
from dotenv import load_dotenv
import os

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

# Regex to extract postcode (4-5 digits) from address
POSTCODE_PATTERN = re.compile(r"\b\d{4,5}\b")


def fetch_mcdonalds_data():
    """Fetch data from McDonald's API and return the parsed JSON response."""
    try:
        response = requests.post(URL, data=PAYLOAD, timeout=10)
        response.raise_for_status()
        return json.loads(response.content.decode("utf-8-sig"))  # Handle UTF-8 BOM
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        print(f"Error fetching data: {e}")
        return None


def extract_store_details(store):
    """Extract relevant details from store data."""
    name = store.get("name", "N/A")
    address = store.get("address", "N/A")
    postcode_match = POSTCODE_PATTERN.search(address)
    postcode = postcode_match.group(0) if postcode_match else None
    city = "Kuala Lumpur"
    state = "Kuala Lumpur"
    country = "Malaysia"
    latitude, longitude = store.get("lat", None), store.get("lng", None)

    # Check for 24-hour operation
    categories = store.get("cat", [])
    operating_hours = "24 Hours" if any(cat.get("cat_name") == "24 Hours" for cat in categories) else "Not Available"

    # Generate Waze link
    waze_link = f"https://www.waze.com/live-map/directions?navigate=yes&to=ll.{latitude}%2C{longitude}" if latitude and longitude else None

    return (name, address, postcode, city, state, country, latitude, longitude, operating_hours, waze_link)


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
                address TEXT,
                postcode TEXT,
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
            INSERT INTO mcdonalds_stores (name, address, postcode, city, state, country, latitude, longitude, operating_hours, waze_link)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
        save_to_database(data["stores"])
    else:
        print("Error: API response does not contain 'stores' key.")
