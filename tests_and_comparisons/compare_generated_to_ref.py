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

def summarize(ops):
    counts = {}
    type_counts = {}
    style_keys = set()
    rect_styles = []
    line_styles = []
    for op in ops:
        if not isinstance(op, list) or len(op) < 2:
            continue
        code = op[0]
        counts[code] = counts.get(code, 0) + 1
        if code == 3 and len(op) > 2:
            t = op[2]
            type_counts[t] = type_counts.get(t, 0) + 1
            if len(op) > 4 and isinstance(op[4], list):
                for i in range(0, len(op[4]) - 1, 2):
                    style_keys.add(op[4][i])
                if t == 6:
                    rect_styles.append(op[4])
                elif t == 153:
                    line_styles.append(op[4])
    return counts, type_counts, sorted(style_keys), rect_styles, line_styles

def main():
    gen = get_inner('generated_grid_payload.json')
    ref = get_inner('clipboard_iterations/test_grid_view/copied_structure.json')

    gen_ops = gen.get('resolved', [])
    ref_ops = ref.get('resolved', [])

    print(f"Generated ops: {len(gen_ops)}")
    print(f"Reference ops: {len(ref_ops)}")

    gc, gtc, gsk, grs, gls = summarize(gen_ops)
    rc, rtc, rsk, rrs, rls = summarize(ref_ops)

    print("\n=== Op-code counts ===")
    all_codes = sorted(set(gc.keys()) | set(rc.keys()))
    for c in all_codes:
        marker = ' ' if gc.get(c) == rc.get(c) else '!'
        print(f"{marker} opcode {c}: generated {gc.get(c, 0)}, reference {rc.get(c, 0)}")

    print("\n=== Shape type counts ===")
    all_types = sorted(set(gtc.keys()) | set(rtc.keys()))
    for t in all_types:
        marker = ' ' if gtc.get(t) == rtc.get(t) else '!'
        print(f"{marker} type {t}: generated {gtc.get(t, 0)}, reference {rtc.get(t, 0)}")

    print("\n=== Style keys present ===")
    print(f"Generated: {gsk}")
    print(f"Reference: {rsk}")

    print("\n=== First rectangle style comparison ===")
    if grs:
        print(f"Generated rect style: {grs[0]}")
    if rrs:
        print(f"Reference rect style: {rrs[0]}")

    print("\n=== First line style comparison ===")
    if gls:
        print(f"Generated line style: {gls[0]}")
    if rls:
        print(f"Reference line style: {rls[0]}")

    print("\n=== Autotext entries ===")
    print(f"Generated: {len(gen.get('autotext_content', {}))}")
    print(f"Reference: {len(ref.get('autotext_content', {}))}")

if __name__ == '__main__':
    main()
