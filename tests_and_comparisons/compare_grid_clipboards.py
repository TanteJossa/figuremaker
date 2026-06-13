import json
import sys

def get_inner_payload(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if 'application/x-vnd.google-docs-drawings-object+wrapped' in data:
        wrapped = data['application/x-vnd.google-docs-drawings-object+wrapped']
        if isinstance(wrapped, str):
            wrapped = json.loads(wrapped)
        inner = json.loads(wrapped.get('data', '{}'))
        return inner
    return data

def summarize_ops(ops):
    counts = {
        'total': len(ops),
        'shape_6_rect': 0,
        'shape_8_ellipse': 0,
        'shape_108_text': 0,
        'shape_153_line': 0,
        'opcode_15_text_insert': 0,
        'opcode_17_format': 0,
        'opcode_2_group': 0,
    }
    text_contents = []
    stroke_weights = []
    coords_x = []
    coords_y = []
    scales_x = []
    scales_y = []
    
    for op in ops:
        if not isinstance(op, list) or len(op) < 2:
            continue
        op_code = op[0]
        
        if op_code == 3 and len(op) > 2:
            shape_type = op[2]
            if shape_type == 6:
                counts['shape_6_rect'] += 1
            elif shape_type == 8:
                counts['shape_8_ellipse'] += 1
            elif shape_type == 108:
                counts['shape_108_text'] += 1
            elif shape_type == 153:
                counts['shape_153_line'] += 1
            
            # Transform matrix
            if isinstance(op[3], list) and len(op[3]) >= 6:
                sx, sy, tx, ty = op[3][0], op[3][3], op[3][4], op[3][5]
                scales_x.append(sx)
                scales_y.append(sy)
                coords_x.append(tx)
                coords_y.append(ty)
                
                # Style list
                if len(op) > 4 and isinstance(op[4], list):
                    for i in range(0, len(op[4]) - 1, 2):
                        if op[4][i] == 22:
                            stroke_weights.append(op[4][i+1])
                            
        elif op_code == 15:
            counts['opcode_15_text_insert'] += 1
            if len(op) > 4 and isinstance(op[4], str):
                text_contents.append(op[4])
        elif op_code == 17:
            counts['opcode_17_format'] += 1
        elif op_code == 2:
            counts['opcode_2_group'] += 1
    
    return {
        'counts': counts,
        'text_contents': sorted(text_contents),
        'stroke_weights': sorted(set(stroke_weights)),
        'coords': {
            'x_min': min(coords_x) if coords_x else None,
            'x_max': max(coords_x) if coords_x else None,
            'y_min': min(coords_y) if coords_y else None,
            'y_max': max(coords_y) if coords_y else None,
        },
        'scales': {
            'x_min': min(scales_x) if scales_x else None,
            'x_max': max(scales_x) if scales_x else None,
            'y_min': min(scales_y) if scales_y else None,
            'y_max': max(scales_y) if scales_y else None,
        }
    }

def compare_text_contents(a, b, label_a='User', label_b='Reference'):
    set_a = set(a)
    set_b = set(b)
    only_in_a = sorted(set_a - set_b)
    only_in_b = sorted(set_b - set_a)
    
    print(f"\n--- Text Content Differences ---")
    print(f"{label_a} unique text count: {len(only_in_a)}")
    print(f"{label_b} unique text count: {len(only_in_b)}")
    if only_in_a:
        print(f"Only in {label_a}:")
        for t in only_in_a[:20]:
            print(f"  - '{t}'")
    if only_in_b:
        print(f"Only in {label_b}:")
        for t in only_in_b[:20]:
            print(f"  - '{t}'")

def main():
    user_path = 'last_clipboard_failed.json'
    ref_path = 'clipboard_iterations/test_grid_view/copied_structure.json'
    
    user_inner = get_inner_payload(user_path)
    ref_inner = get_inner_payload(ref_path)
    
    user_summary = summarize_ops(user_inner.get('resolved', []))
    ref_summary = summarize_ops(ref_inner.get('resolved', []))
    
    print("=== OPERATION COUNT COMPARISON ===")
    for key in user_summary['counts']:
        u = user_summary['counts'][key]
        r = ref_summary['counts'][key]
        marker = " " if u == r else "!"
        print(f"{marker} {key:<25} | User: {u:<5} | Ref: {r:<5}")
    
    print("\n=== COORDINATE RANGE COMPARISON ===")
    print(f"  User X range: {user_summary['coords']['x_min']} to {user_summary['coords']['x_max']}")
    print(f"  Ref  X range: {ref_summary['coords']['x_min']} to {ref_summary['coords']['x_max']}")
    print(f"  User Y range: {user_summary['coords']['y_min']} to {user_summary['coords']['y_max']}")
    print(f"  Ref  Y range: {ref_summary['coords']['y_min']} to {ref_summary['coords']['y_max']}")
    
    print("\n=== SCALE RANGE COMPARISON ===")
    print(f"  User scale X range: {user_summary['scales']['x_min']:.6f} to {user_summary['scales']['x_max']:.6f}")
    print(f"  Ref  scale X range: {ref_summary['scales']['x_min']:.6f} to {ref_summary['scales']['x_max']:.6f}")
    print(f"  User scale Y range: {user_summary['scales']['y_min']:.6f} to {user_summary['scales']['y_max']:.6f}")
    print(f"  Ref  scale Y range: {ref_summary['scales']['y_min']:.6f} to {ref_summary['scales']['y_max']:.6f}")
    
    print("\n=== STROKE WEIGHT COMPARISON ===")
    print(f"  User stroke weights: {user_summary['stroke_weights']}")
    print(f"  Ref  stroke weights: {ref_summary['stroke_weights']}")
    
    compare_text_contents(user_summary['text_contents'], ref_summary['text_contents'], 'User', 'Reference')
    
    # Check autotext counts
    print(f"\n=== AUTOTEXT CONTENT ===")
    print(f"  User autotext keys: {len(user_inner.get('autotext_content', {}))}")
    print(f"  Ref  autotext keys: {len(ref_inner.get('autotext_content', {}))}")

if __name__ == '__main__':
    main()
