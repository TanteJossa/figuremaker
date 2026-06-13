import json
from collections import Counter

def get_inner(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if 'application/x-vnd.google-docs-drawings-object+wrapped' in data:
        wrapped = data['application/x-vnd.google-docs-drawings-object+wrapped']
        if isinstance(wrapped, str):
            wrapped = json.loads(wrapped)
        inner = json.loads(wrapped.get('data', '{}'))
        return inner
    return data

def inspect(path, label):
    inner = get_inner(path)
    ops = inner.get('resolved', [])
    line_ops = [op for op in ops if isinstance(op, list) and len(op) > 2 and op[0] == 3 and op[2] == 153]
    print(f"\n=== {label}: {len(line_ops)} line ops ===")
    ids = Counter(op[1] for op in line_ops)
    print(f"Distinct line ids: {len(ids)}")
    print("Top ids by count:", ids.most_common(10))
    print("First 5 line ops:")
    for op in line_ops[:5]:
        print(op)

inspect('generated_grid_payload.json', 'Generated')
inspect('clipboard_iterations/test_grid_view/copied_structure.json', 'Reference')
