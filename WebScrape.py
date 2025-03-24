import requests
import json
import psycopg2
import re
from dotenv import load_dotenv
import os
import googlemaps

# Load environment variables
load_dotenv()

# PostgreSQL Database Config
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

# API Payload (Filtering for Kuala Lumpur outlets)
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

# Regex pattern for Kuala Lumpur addresses
KL_ADDRESS_PATTERN = re.compile(r"\b\d{4,5}\b.*Kuala Lumpur", re.IGNORECASE)

def fetch_mcdonalds_data():
    """Fetch data from McDonald's API and return the parsed JSON response."""
    try:
        response = requests.post(URL, data=PAYLOAD, timeout=10)
        response.raise_for_status()
        return json.loads(response.content.decode("utf-8-sig"))
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        print(f"Error fetching data: {e}")
        return None

def geocode_address(name, address):
    """Retrieve latitude and longitude from a store name and address using Google Maps API."""
    try:
        query = f"{name}, {address}, Kuala Lumpur, Malaysia"
        geocode_result = gmaps.geocode(query)
        
        if geocode_result:
            location = geocode_result[0]["geometry"]["location"]
            return location["lat"], location["lng"]
    except Exception as e:
        print(f"Geocoding error for {query}: {e}")
    return None, None


def filter_kl_stores(stores):
    """Filter and return only Kuala Lumpur outlets with a valid address."""
    return list(filter(lambda store: KL_ADDRESS_PATTERN.search(store.get("address", "")), stores))

def extract_store_details(store):
    """Extract relevant store details from the API response."""
    name = store.get("name", "N/A")
    address = store.get("address", "N/A")
    city, state, country = "Kuala Lumpur", "Kuala Lumpur", "Malaysia"

    # Use store name and address for geocoding
    latitude, longitude = geocode_address(name, address)

    operating_hours = "24 Hours" if any(cat.get("cat_name") == "24 Hours" for cat in store.get("cat", [])) else "Not Available"
    waze_link = f"https://www.waze.com/live-map/directions?navigate=yes&to=ll.{latitude}%2C{longitude}" if latitude and longitude else ""

    # Extract features
    features = [cat.get("cat_name") for cat in store.get("cat", []) if cat.get("cat_name")]

    return (name, address, city, state, country, latitude, longitude, operating_hours, waze_link, features)


def save_to_database(stores):
    """Save store data to PostgreSQL, including features."""
    if not stores:
        print("No stores to save.")
        return

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # Ensure the tables exist
        cur.execute("""
            CREATE TABLE IF NOT EXISTS mcdonalds_stores (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                address TEXT UNIQUE NOT NULL,
                city TEXT NOT NULL,
                state TEXT NOT NULL,
                country TEXT NOT NULL DEFAULT 'Malaysia',
                latitude DOUBLE PRECISION,
                longitude DOUBLE PRECISION,
                operating_hours TEXT,
                waze_link TEXT
            );
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS features (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS outlet_features (
                outlet_id INT REFERENCES mcdonalds_stores(id) ON DELETE CASCADE,
                feature_id INT REFERENCES features(id) ON DELETE CASCADE,
                PRIMARY KEY (outlet_id, feature_id)
            );
        """)

        # Insert store data
        store_insert_query = """
            INSERT INTO mcdonalds_stores (name, address, city, state, country, latitude, longitude, operating_hours, waze_link)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (name) DO NOTHING
            RETURNING id;
        """

        # Insert feature data
        feature_insert_query = """
            INSERT INTO features (name)
            VALUES (%s)
            ON CONFLICT (name) DO NOTHING
            RETURNING id;
        """

        # Insert outlet-feature mapping
        outlet_feature_insert_query = """
            INSERT INTO outlet_features (outlet_id, feature_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING;
        """

        store_data = [extract_store_details(store) for store in stores]
        
        for store_entry in store_data:
            name, address, city, state, country, latitude, longitude, operating_hours, waze_link, features = store_entry

            # Insert store and get its ID
            cur.execute(store_insert_query, (name, address, city, state, country, latitude, longitude, operating_hours, waze_link))
            store_id = cur.fetchone()

            if store_id is None:
                cur.execute("SELECT id FROM mcdonalds_stores WHERE name = %s;", (name,))
                store_id = cur.fetchone()[0]
            else:
                store_id = store_id[0]

            # Insert features and map them to the store
            for feature in features:
                cur.execute(feature_insert_query, (feature,))
                feature_id = cur.fetchone()

                if feature_id is None:
                    cur.execute("SELECT id FROM features WHERE name = %s;", (feature,))
                    feature_id = cur.fetchone()[0]
                else:
                    feature_id = feature_id[0]

                # Link outlet to features
                cur.execute(outlet_feature_insert_query, (store_id, feature_id))

        conn.commit()
        print(f"✅ {len(store_data)} stores and their features saved to database.")
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
