import os
import json
import sys
import google.generativeai as genai
from PIL import Image

# Setup Gemini
# You must set your GEMINI_API_KEY environment variable
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY environment variable not set.")
    sys.exit(1)

genai.configure(api_key=api_key)

# Detailed prompt to match Compass7 JSON schema
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
1. Days must be: Monday, Tuesday, Wednesday, Thursday, Friday.
2. Periods are usually 1-10 plus a "Lunch Period".
3. If multiple subjects are in one box (electives), list them all in 'options'.
4. For empty boxes, use "None" as the subject.
5. Extract the start and end times for each period accurately.
6. Output ONLY the raw JSON. No markdown blocks.
"""

def convert_image_to_json(image_path, output_path="timetable_data.json"):
    if not os.path.exists(image_path):
        print(f"Error: File {image_path} not found.")
        return

    print(f"Processing image: {image_path}...")
    
    try:
        # Load image
        img = Image.open(image_path)
        
        # Initialize model
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        # Generate content
        response = model.generate_content([PROMPT, img])
        
        # Clean and parse JSON
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:-3]
        elif text.startswith("```"):
            text = text[3:-3]
            
        data = json.loads(text)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            
        print(f"Successfully converted! Data saved to: {output_path}")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        if hasattr(response, 'text'):
            print("Model response was:")
            print(response.text)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_timetable.py <path_to_image.png>")
    else:
        convert_image_to_json(sys.argv[1])
