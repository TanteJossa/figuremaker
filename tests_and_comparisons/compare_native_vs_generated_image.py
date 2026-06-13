import json
from graph_engine import compile_latex_to_png
from slides_builder import SlidesBuilder

# Load captured native payload.
with open("last_clipboard.json", "r", encoding="utf-8") as f:
    native = json.load(f)

def wrap_inner(wrapper):
    if isinstance(wrapper, dict):
        w = wrapper
    else:
        w = json.loads(wrapper)
    return json.loads(w["data"])

native_drawing_inner = wrap_inner(native["application/x-vnd.google-docs-drawings-object+wrapped"])
native_doc_inner = wrap_inner(native["application/x-vnd.google-docs-document-slice-clip+wrapped"])
native_image_inner = wrap_inner(native["application/x-vnd.google-docs-image-clip+wrapped"])

# Build generated payload for the same image.
# Use the same Drive URL and intrinsic size as the native capture.
drive_url = "https://drive.google.com/uc?id=1d4wQ-xMRo-hgWEt_fj50GFAuXvQ_Q-Ps&export=download"
native_w, native_h = 260, 54
width_pt = 296.7308 * native_w / 508.0
height_pt = 296.7498 * native_h / 508.0

builder = SlidesBuilder(font_family='Ubuntu')
builder.add_image(
    x=138393.336 / 508.0,
    y=40410.7203 / 508.0,
    width_pt=width_pt,
    height_pt=height_pt,
    image_url=drive_url,
    native_width_px=native_w,
    native_height_px=native_h,
    obj_id='slide_c1050e194a62_element_1021_text',
)
gen = builder.to_punch()
gen_drawing_inner = json.loads(gen["flat"])

gen_doc_wrapper = json.loads(gen["document_slice_wrapped"])
gen_doc_inner = json.loads(gen_doc_wrapper["data"])

gen_image_wrapper = json.loads(gen["image_clip_wrapped"])
gen_image_inner = json.loads(gen_image_wrapper["data"])

print("=== DRAWING FLAT DIFF (native vs generated) ===")
print(json.dumps(native_drawing_inner, indent=2, sort_keys=True))
print("---")
print(json.dumps(gen_drawing_inner, indent=2, sort_keys=True))

print("\n=== DOCUMENT SLICE DIFF ===")
print(json.dumps(native_doc_inner, indent=2, sort_keys=True))
print("---")
print(json.dumps(gen_doc_inner, indent=2, sort_keys=True))

print("\n=== IMAGE CLIP DIFF ===")
print(json.dumps(native_image_inner, indent=2, sort_keys=True))
print("---")
print(json.dumps(gen_image_inner, indent=2, sort_keys=True))

print("\n=== WRAPPER META DIFF ===")
for key in ["application/x-vnd.google-docs-document-slice-clip+wrapped",
            "application/x-vnd.google-docs-drawings-object+wrapped",
            "application/x-vnd.google-docs-image-clip+wrapped"]:
    nw = json.loads(native[key])
    if key == "application/x-vnd.google-docs-document-slice-clip+wrapped":
        gw = gen_doc_wrapper
    elif key == "application/x-vnd.google-docs-drawings-object+wrapped":
        gw = json.loads(gen["wrapped"])
    else:
        gw = gen_image_wrapper
    print(f"{key}:")
    print(f"  native dih={nw['dih']} edi={nw['edi'][:20]}... edrk={nw['edrk'][:20]}...")
    print(f"  gen    dih={gw['dih']} edi={gw['edi'][:20]}... edrk={gw['edrk'][:20]}...")
