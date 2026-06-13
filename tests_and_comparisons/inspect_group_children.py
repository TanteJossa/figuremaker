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
    print(f"\n=== {label} ===")
    for i, op in groups:
        children = op[2]
        print(f"Group {op[1]} at {i}: children {len(children)}")
        print(f"  first 10: {children[:10]}")
        print(f"  last 5: {children[-5:]}")

inspect('generated_grid_payload.json', 'Generated')
inspect('clipboard_iterations/test_grid_view/copied_structure.json', 'Reference')
