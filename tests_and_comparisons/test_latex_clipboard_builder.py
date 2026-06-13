import json
from slides_builder import SlidesBuilder

b = SlidesBuilder(font_family='Ubuntu')
b.add_image(
    x=272.4, y=79.5,
    width_pt=151.87, height_pt=31.54,
    image_url='https://drive.google.com/uc?id=TEST&export=download',
    native_width_px=260, native_height_px=54,
    obj_id='slide_test_element_1_text'
)

payload = b.to_punch()
print("Wrapped keys:", list(payload.keys()))
print("Drawings object flat (pretty):")
flat = json.loads(payload['flat'])
print(json.dumps(flat, indent=2)[:2000])

if 'document_slice_wrapped' in payload:
    print("\nDocument slice present")
    doc = json.loads(payload['document_slice_wrapped'])
    print(json.dumps(doc, indent=2)[:1500])

if 'image_clip_wrapped' in payload:
    print("\nImage clip present")
    img = json.loads(payload['image_clip_wrapped'])
    print(json.dumps(img, indent=2))
