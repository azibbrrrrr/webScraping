import os
import logging
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize OpenAI client
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)

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

# Test function
def test_extract_features():
    test_queries = [
        "Which outlets in KL operate 24 hours",
        "Which outlet allows birthday parties",
        "Show me a McDonald's open 24 hours with a Digital Order Kiosk.",
        "I need a place with McDelivery and WiFi.",
        "Is there a McDonald's with a Drive-Thru and McCafe nearby?",
        "Find an outlet that supports Cashless Facility and has a Dessert Center.",
        "I need an outlet that serves Breakfast and has a Surau.",
        "Where can I find a McDonald's with an Electric Vehicle charging station and a Digital Order Kiosk?",
        "Which McDonald's outlets have a Birthday Party facility and McCafe?",
        "Can you show me a McDonald's with WiFi and open 24 hours?",
        "Looking for an outlet with a Dessert Center and Drive-Thru.",
        "Does this location offer Cashless Facility and McDelivery?",
        "Find a McDonald's with Electric Vehicle charging and Breakfast service."
    ]
    
    for query in test_queries:
        extracted_features = extract_features_llm(query)
        print(f"Query: {query}\nExtracted Features: {extracted_features}\n")

if __name__ == "__main__":
    test_extract_features()
