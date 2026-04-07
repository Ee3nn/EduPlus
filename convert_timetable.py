import os
import json
import sys
import base64
from openai import AzureOpenAI

# Setup Azure OpenAI
api_key = os.environ.get("AZURE_OPENAI_KEY")
endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT")
api_version = os.environ.get("AZURE_OPENAI_VERSION", "2024-02-01")

if not all([api_key, endpoint, deployment]):
    print("Error: Azure environment variables not fully set.")
    sys.exit(1)

client = AzureOpenAI(
    api_key=api_key,  
    api_version=api_version,
    azure_endpoint=endpoint
)

PROMPT = """
You are a precision data extraction tool. Your task is to convert the provided school timetable image into a COMPLETE and VALID JSON object.

CRITICAL INSTRUCTIONS:
1. Process EVERY day (Monday, Tuesday, Wednesday, Thursday, Friday).
2. Process EVERY period (usually 1 through 10, plus "Lunch Period" and any early/late slots).
3. Do NOT truncate the output. You must provide the full 5-day schedule.
4. If a box has multiple subjects (electives), list them ALL in the 'options' array.
5. Extract the start/end times exactly as shown in the image.

TARGET SCHEMA:
{
  "timetable": {
    "class": "Class Name from image",
    "schedule": [
      {
        "day": "Monday",
        "periods": [
          {
            "period": "1",
            "time": "8:00 - 8:40",
            "options": [
              { "subject": "Subject", "room": "Room" }
            ]
          }
        ]
      },
      ... repeat for all days ...
    ]
  }
}

RULES:
- Empty slot = { "subject": "None", "room": null }
- Output ONLY raw JSON. No conversational text.
"""

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def convert_image_to_json(image_path, output_path="timetable_data.json"):
    if not os.path.exists(image_path):
        print(f"Error: File {image_path} not found.")
        return

    print(f"Processing FULL image with Azure GPT-4o...")
    
    try:
        base64_image = encode_image(image_path)
        
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
            max_tokens=4096, # Increased to ensure full output
            temperature=0,    # Set to 0 for maximum precision
        )
        
        text = response.choices[0].message.content.strip()
        
        if "{" in text:
            start = text.find("{")
            end = text.rfind("}") + 1
            text = text[start:end]
            
        data = json.loads(text)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            
        print(f"Successfully converted! Data saved to: {output_path}")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_timetable.py <path_to_image.png>")
    else:
        convert_image_to_json(sys.argv[1])
