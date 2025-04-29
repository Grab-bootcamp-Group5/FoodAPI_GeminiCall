import os
import time
import logging
from datetime import datetime
import json
from google import genai

# Configuration
GOOGLE_API_KEY = "API Google Gemini"
client = genai.Client(api_key=GOOGLE_API_KEY)
OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(OUTPUT_FOLDER, 'extract_food_ingredients.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Rate limiting: 25 requests/minute
def respect_rate_limit():
    interval = 60 / 25
    time.sleep(interval)


def analyze_food(dish_name: str, retries: int = 3) -> dict:
    prompt = f"""
    List the most important ingredients to cook \"{dish_name}\".
    Return a JSON array named \"ingredients\", where each element has:
    - ingredient_name (string)
    - total unit (return how much \"g\" for solids or \"ml\" for liquids)
    - category: classify the ingredients into these list of given categories:
    CATEGORIES = [
    "Prepared Vegetables", "Vegetables", "Fresh Fruits", "Fresh Meat",
    "Seafood & Fish Balls", "Instant Foods", "Ice Cream & Cheese", "Cakes",
    "Dried Fruits", "Candies", "Fruit Jam", "Snacks", "Milk", "Yogurt",
    "Alcoholic Beverages", "Beverages", "Seasonings", "Grains & Staples",
    "Cold Cuts: Sausages & Ham", "Cereals & Grains"]"""

    default = {"dish": dish_name, "ingredients": []}

    for attempt in range(1, retries + 1):
        try:
            respect_rate_limit()
            response = client.models.generate_content(
                model="gemini-2.0-flash-lite",
                contents=[prompt]
            )
            text = response.text.strip()
            start = text.find('{')
            end = text.rfind('}') + 1
            if start >= 0 and end > start:
                payload = text[start:end]
                data = json.loads(payload)
                if isinstance(data, dict) and data.get('ingredients') is not None:
                    logger.info(f"Extracted ingredients for '{dish_name}'")
                    return data
            logger.warning(f"Unexpected response structure (attempt {attempt})")
        except Exception as e:
            logger.warning(f"Error on attempt {attempt} for '{dish_name}': {e}")
        time.sleep(2 ** attempt)

    logger.error(f"Failed to analyze '{dish_name}' after {retries} attempts")
    return default


def main():
    dish = "hamburger"
    result = analyze_food(dish)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_name = dish.replace(' ', '_')
    out_path = os.path.join(OUTPUT_FOLDER, f"{safe_name}.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved analysis to {out_path}")


if __name__ == '__main__':
    main()
