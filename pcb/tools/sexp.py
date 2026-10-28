import re, copy
TOK = re.compile(r'\s*(\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+)')


class Sym(str):
    pass


def unq(s):
    out = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == '\\' and i + 1 < len(s):
            n = s[i + 1]
            out.append({'n': '\n', 't': '\t'}.get(n, n))
            i += 2
        else:
            out.append(c)
            i += 1
    return ''.join(out)


def parse(t):
    stack = [[]]
    for m in TOK.finditer(t):
        tok = m.group(1)
        if tok == '(':
            stack.append([])
        elif tok == ')':
            x = stack.pop()
            stack[-1].append(x)
        elif tok.startswith('"'):
            stack[-1].append(unq(tok[1:-1]))
        else:
            stack[-1].append(Sym(tok))
    return stack[0]


def q(s):
    s = str(s).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
    return '"' + s + '"'


def num(v):
    s = ('%.4f' % v).rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


def dump(x, ind=0):
    if isinstance(x, list):
        if not x:
            return '()'
        if all(not isinstance(e, list) for e in x):
            return '(' + ' '.join(dump(e) for e in x) + ')'
        s = '(' + dump(x[0])
        for e in x[1:]:
            if isinstance(e, list):
                s += '\n' + '\t' * (ind + 1) + dump(e, ind + 1)
            else:
                s += ' ' + dump(e)
        return s + '\n' + '\t' * ind + ')'
    if isinstance(x, Sym):
        return str(x)
    if isinstance(x, bool):
        return 'yes' if x else 'no'
    if isinstance(x, (int, float)):
        return num(float(x))
    return q(x)


def find(x, key):
    return [e for e in x if isinstance(e, list) and e and e[0] == key]


LIBDIR = r'C:\Program Files\KiCad\10.0\share\kicad\symbols'
_cache = {}


def libsyms(lib):
    if lib not in _cache:
        t = open(LIBDIR + '\\' + lib + '.kicad_sym', encoding='utf8').read()
        root = parse(t)[0]
        _cache[lib] = {e[1]: e for e in find(root, 'symbol')}
    return _cache[lib]


def getsym(lib, name):
    """Return a flattened copy of a library symbol (resolves 'extends')."""
    s = copy.deepcopy(libsyms(lib)[name])
    ex = find(s, 'extends')
    if not ex:
        return s
    par = getsym(lib, ex[0][1])
    props = {p[1]: p for p in find(s, 'property')}
    attrs = {e[0]: e for e in s[2:] if isinstance(e, list) and e[0] not in ('property', 'symbol', 'extends')}
    out = [Sym('symbol'), name]
    for e in par[2:]:
        if isinstance(e, list) and e[0] in attrs:
            out.append(attrs.pop(e[0]))
        elif isinstance(e, list) and e[0] == 'property' and e[1] in props:
            out.append(props.pop(e[1]))
        elif isinstance(e, list) and e[0] == 'symbol':
            e = copy.deepcopy(e)
            e[1] = name + e[1][len(par[1]):]
            out.append(e)
        else:
            out.append(e)
    # child-only attributes / properties the parent does not have
    pos = 2 + sum(1 for e in out[2:] if isinstance(e, list) and e[0] != 'property' and e[0] != 'symbol')
    for e in attrs.values():
        out.insert(pos, e)
    for p in props.values():
        idx = max(i for i, e in enumerate(out) if isinstance(e, list) and e[0] == 'property') + 1
        out.insert(idx, p)
    return out


def pins(sym):
    res = []

    def walk(x, unit):
        for e in x:
            if isinstance(e, list) and e and e[0] == 'symbol':
                walk(e, int(e[1].rsplit('_', 2)[-2]))
            elif isinstance(e, list) and e and e[0] == 'pin':
                at = find(e, 'at')[0]
                res.append(dict(type=str(e[1]), x=float(at[1]), y=float(at[2]),
                                a=float(at[3]) if len(at) > 3 else 0.0,
                                name=find(e, 'name')[0][1], num=find(e, 'number')[0][1],
                                unit=unit))
    walk(sym, 0)
    return res
