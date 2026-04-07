import sys
import json
try:
    import docx
except ImportError:
    print("Please run: pip install python-docx")
    sys.exit(1)

TIMES = {
    "1": "8:00 - 8:40",
    "2": "8:45 - 9:25",
    "3": "9:35 - 10:15",
    "4": "10:20 - 11:00",
    "5": "11:05 - 11:55",
    "Lunch Period": "12:00 - 12:40",
    "6": "12:45 - 13:25",
    "7": "13:30 - 14:10",
    "8": "14:15 - 14:55",
    "9": "15:00 - 15:40",
    "10": "15:45 - 16:25",
}

def parse_docx(file_path):
    doc = docx.Document(file_path)
    table = doc.tables[0]
    
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    schedule = {day: [] for day in days}
    
    for row in table.rows[1:]: # Skip header
        period = row.cells[0].text.strip()
        time = TIMES.get(period, "00:00 - 00:00")
        
        for i, day in enumerate(days):
            cell_text = row.cells[i+1].text.strip()
            subjects = [s.strip() for s in cell_text.split('\n') if s.strip()]
            options = [{"subject": s, "room": None} for s in subjects]
            if not options:
                options = [{"subject": "None", "room": None}]
                
            schedule[day].append({
                "period": period,
                "time": time,
                "options": options
            })
            
    return {
        "timetable": {
            "class": "IB Grade 10 Class 8",
            "schedule": [{"day": day, "periods": schedule[day]} for day in days]
        }
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_timetable.py <file.docx>")
        sys.exit(1)
        
    try:
        data = parse_docx(sys.argv[1])
        with open("timetable_data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print("Successfully converted! Data saved to: timetable_data.json")
    except Exception as e:
        print(f"Error parsing document: {e}")
