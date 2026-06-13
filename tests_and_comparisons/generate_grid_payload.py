import json
import sys
sys.path.insert(0, '.')
from app import convert_to_google_slides_json

def main():
    with open('test_graph_grid.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    compiled = convert_to_google_slides_json(data.get('elements', []), data.get('font_family', 'Ubuntu'))

    # Save the flat inner payload
    flat = json.loads(compiled['flat'])
    with open('generated_grid_payload.json', 'w', encoding='utf-8') as f:
        json.dump(flat, f, indent=2)
    print(f"Wrote generated_grid_payload.json: {len(flat.get('resolved', []))} ops")

    # Also save wrapped form for clipboard simulation
    wrapped = json.loads(compiled['wrapped'])
    with open('generated_grid_wrapped.json', 'w', encoding='utf-8') as f:
        json.dump(wrapped, f, indent=2)
    print(f"Wrote generated_grid_wrapped.json")

if __name__ == '__main__':
    main()
