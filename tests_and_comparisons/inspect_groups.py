import json

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
    groups = [(i, op) for i, op in enumerate(ops) if isinstance(op, list) and op[0] == 2]
    print(f"\n=== {label}: {len(groups)} groups ===")
    for i, op in groups:
        print(f"index {i}: id={op[1]}, children={len(op[2])}, transform={op[3]}")

inspect('generated_grid_payload.json', 'Generated')
inspect('clipboard_iterations/test_grid_view/copied_structure.json', 'Reference')
