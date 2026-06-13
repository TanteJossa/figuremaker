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

def summarize(ops):
    counts = {}
    type_counts = {}
    style_keys = set()
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
    return counts, type_counts, sorted(style_keys)

def main():
    gen = get_inner('generated_sine_payload.json')
    ref = get_inner('clipboard_iterations/test_sine_wave/copied_structure.json')
    go = gen.get('resolved', [])
    ro = ref.get('resolved', [])
    print(f"Generated ops: {len(go)}, Reference ops: {len(ro)}")
    gc, gtc, gsk = summarize(go)
    rc, rtc, rsk = summarize(ro)
    print("Op counts:")
    for c in sorted(set(gc)|set(rc)):
        print(f" {' ' if gc.get(c)==rc.get(c) else '!'} opcode {c}: gen {gc.get(c,0)} ref {rc.get(c,0)}")
    print("Shape types:")
    for t in sorted(set(gtc)|set(rtc)):
        print(f" {' ' if gtc.get(t)==rtc.get(t) else '!'} type {t}: gen {gtc.get(t,0)} ref {rtc.get(t,0)}")
    print(f"Style keys gen: {gsk}")
    print(f"Style keys ref: {rsk}")
    print(f"Autotext gen: {len(gen.get('autotext_content',{}))} ref: {len(ref.get('autotext_content',{}))}")

if __name__ == '__main__':
    main()
