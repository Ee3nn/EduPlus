import os
import json
import sys
import google.generativeai as genai
from typing import List

# Setup Gemini
# You must set your GEMINI_API_KEY environment variable
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# Detailed prompt to match Compass7 JSON schema
PROMPT = """
You are a specialized OCR and data extraction assistant for school timetables.
Analyze the provided document (image or PDF) and convert it into a strictly formatted JSON object.

TARGET SCHEMA:
{
  "timetable": {
    "class": "Class Name (e.g., IB Grade 10 Class 8)",
    "schedule": [
      {
        "day": "Monday",
        "periods": [
          {
            "period": "1",
            "time": "8:00 - 8:40",
            "options": [
              { "subject": "Subject Name", "room": "Room (or null)" }
            ]
          }
        ]
      }
    ]
  }
}

RULES:
1. Days must be: Monday, Tuesday, Wednesday, Thursday, Friday.
2. If multiple subjects share the same time slot (electives), list them all in the 'options' array.
3. If only one subject exists, the 'options' array should have one object.
4. For empty slots or break times, use "None" or "Lunch" as the subject.
5. Times must be in 'HH:MM - HH:MM' format.
6. Rooms should be strings if present, otherwise null.
7. Output ONLY the raw JSON. No markdown code blocks.
"""

def convert_timetable(file_path: str, output_path: str = "timetable_data.json"):
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        return

    # Choose a model
    model = genai.GenerativeModel("gemini-1.5-flash")

    print(f"Uploading {file_path}...")
    sample_file = genai.upload_file(path=file_path)

    print("Generating JSON structure...")
    response = model.generate_content([sample_file, PROMPT])

    try:
        # Clean response text in case model adds markdown blocks
        clean_json = response.text.strip().replace("```json", "").replace("```", "")
        data = json.loads(clean_json)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ensure_ascii=False)
            
        print(f"Successfully converted! Data saved to: {output_path}")
        print("\nYou can now copy the contents of this file into the 'TIMETABLE_DATA' variable in your static/index.html.")
        
    except json.JSONDecodeError:
        print("Error: Model did not return valid JSON. Response received:")
        print(response.text)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_timetable.py <path_to_timetable_image_or_pdf>")
    else:
        file_arg = sys.argv[1]
        convert_timetable(file_arg)
