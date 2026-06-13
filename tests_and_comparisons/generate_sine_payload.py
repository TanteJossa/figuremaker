import json
import sys
sys.path.insert(0, '.')
from app import convert_to_google_slides_json

def main():
    with open('test_sinus_graph.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    compiled = convert_to_google_slides_json(data.get('elements', []), data.get('font_family', 'Ubuntu'))
    flat = json.loads(compiled['flat'])
    with open('generated_sine_payload.json', 'w', encoding='utf-8') as f:
        json.dump(flat, f, indent=2)
    print(f"Wrote generated_sine_payload.json: {len(flat.get('resolved', []))} ops")

if __name__ == '__main__':
    main()
