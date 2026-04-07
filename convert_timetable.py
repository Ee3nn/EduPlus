import os
import json
import sys
import time
from google import genai
from PIL import Image

# Setup Gemini
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY environment variable not set.")
    sys.exit(1)

client = genai.Client(api_key=api_key)

# Detailed prompt
PROMPT = """
Analyze this school timetable image and convert it into a strictly formatted JSON object.

TARGET SCHEMA:
{
  "timetable": {
    "class": "Class Name",
    "schedule": [
      {
        "day": "Monday",
        "periods": [
          {
            "period": "1",
            "time": "8:00 - 8:40",
            "options": [
              { "subject": "Subject Name", "room": null }
            ]
          }
        ]
      }
    ]
  }
}

RULES:
1. Days: Monday, Tuesday, Wednesday, Thursday, Friday.
2. Periods: 1-10 and "Lunch Period".
3. Multiple subjects in one slot? List them all in 'options'.
4. Empty slot? Use "None" as subject.
5. Accurate start/end times.
6. Output ONLY raw JSON. No markdown code blocks.
"""

def convert_image_to_json(image_path, output_path="timetable_data.json"):
    if not os.path.exists(image_path):
        print(f"Error: File {image_path} not found.")
        return

    # Try a few different model names if one is busy or missing
    models_to_try = ["gemini-flash-latest", "gemini-2.0-flash", "gemini-1.5-flash"]
    
    img = Image.open(image_path)
    
    success = False
    for model_id in models_to_try:
        if success: break
        
        print(f"Attempting with model: {model_id}...")
        
        for attempt in range(3): # Retry up to 3 times for quota issues
            try:
                response = client.models.generate_content(
                    model=model_id,
                    contents=[PROMPT, img]
                )
                
                text = response.text.strip()
                
                # Robust JSON extraction
                if "{" in text:
                    start = text.find("{")
                    end = text.rfind("}") + 1
                    text = text[start:end]
                    
                data = json.loads(text)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                    
                print(f"Successfully converted! Data saved to: {output_path}")
                success = True
                break
                
            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg:
                    print(f"Quota exceeded for {model_id}. Waiting 30s (Attempt {attempt+1}/3)...")
                    time.sleep(30)
                elif "404" in err_msg:
                    print(f"Model {model_id} not found, trying next...")
                    break # Break inner loop to try next model
                else:
                    print(f"An unexpected error occurred: {err_msg}")
                    break # Break inner loop

    if not success:
        print("Failed to convert image after trying multiple models and retries.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_timetable.py <path_to_image.png>")
    else:
        convert_image_to_json(sys.argv[1])
