from pathlib import Path
import json, re, unicodedata

MST = Path('/mnt/data/marc.mst')
OUT_JSON = Path('/mnt/data/catalogo_aguapey_actualizado.json')
OUT_JS = Path('/mnt/data/catalog-data.js')

b = MST.read_bytes()
nxt = int.from_bytes(b[4:8], 'little') if len(b) >= 8 else 999999

def valid_header(i):
    if i + 32 > len(b): return None
    mfn = int.from_bytes(b[i:i+4], 'little')
    if not (1 <= mfn < nxt): return None
    mfrl = int.from_bytes(b[i+4:i+8], 'little')
    if not (50 <= mfrl <= 10000 and i + mfrl <= len(b)): return None
    base = int.from_bytes(b[i+12:i+14], 'little')
    if not (24 <= base < mfrl): return None
    tag = int.from_bytes(b[i+18:i+20], 'little')
    pos = int.from_bytes(b[i+20:i+22], 'little')
    ln = int.from_bytes(b[i+22:i+24], 'little')
    if not (tag == 8 and pos == 0 and 5 <= ln <= 30): return None
    data = b[i+base:i+base+ln]
    if not data.startswith(b'##^a'): return None
    return mfn, mfrl, base

# scan for all plausible active/old records; take the latest physical occurrence per MFN
latest = {}
for i in range(64, len(b)-32):
    vh = valid_header(i)
    if vh:
        mfn, mfrl, base = vh
        if mfn not in latest or i > latest[mfn][0]:
            latest[mfn] = (i, mfrl, base)

def decode(raw):
    return raw.decode('cp850', errors='replace').replace('\x00','').strip()

def parse_fields(off, mfrl, base):
    data = b[off+base:off+mfrl]
    fields = []
    for p in range(off+18, off+base, 6):
        if p+6 > off+base: break
        tag = int.from_bytes(b[p:p+2], 'little')
        pos = int.from_bytes(b[p+2:p+4], 'little')
        ln = int.from_bytes(b[p+4:p+6], 'little')
        if tag == 0 and pos == 0 and ln == 0: continue
        if pos < 0 or ln <= 0 or pos+ln > len(data): continue
        fields.append((tag, decode(data[pos:pos+ln])))
    return fields

sub_re = re.compile(r'\^([a-z0-9])')
def strip_indicators(s):
    # MARC fields often start with two indicator chars (##, 1#, 10, 0#)
    return s[2:] if len(s) >= 2 and not s.startswith('^') else s

def subfields(s):
    s = strip_indicators(s)
    parts = sub_re.split(s)
    d = {}
    # text before first subfield ignored unless useful
    for i in range(1, len(parts), 2):
        code = parts[i]
        val = parts[i+1].strip() if i+1 < len(parts) else ''
        if val:
            d.setdefault(code, []).append(val)
    return d

def sf_text(s, code):
    return ' '.join(subfields(s).get(code, [])).strip()

def clean(v):
    v = re.sub(r'\s+', ' ', (v or '')).strip(' ;,./')
    return v

def normalize_isbn(s):
    # keep ISBN-like numbers; do not over-normalize old values
    s = clean(s)
    return s

def first_nonempty(vals):
    for v in vals:
        if clean(v): return clean(v)
    return ''

books=[]
for mfn in sorted(latest):
    off,mfrl,base = latest[mfn]
    fields = parse_fields(off,mfrl,base)
    bytag = {}
    for tag,text in fields:
        bytag.setdefault(tag,[]).append(text)
    authors = []
    for tag in (100, 110, 111, 700, 710, 711):
        for f in bytag.get(tag,[]):
            a = sf_text(f,'a')
            if a and a not in authors: authors.append(clean(a))
    title_parts=[]
    for f in bytag.get(245,[]):
        sf=subfields(f)
        title_parts.extend(sf.get('a',[]))
        # subtitle b can matter
        title_parts.extend(sf.get('b',[]))
    title=clean(' '.join(title_parts))
    responsibility=clean(' '.join(sf_text(f,'c') for f in bytag.get(245,[])))
    edition=clean(' '.join(sf_text(f,'a') for f in bytag.get(250,[])))
    place=clean(' '.join(sf_text(f,'a') for f in bytag.get(260,[])))
    publisher=clean(' '.join(sf_text(f,'b') for f in bytag.get(260,[])))
    year=clean(' '.join(sf_text(f,'c') for f in bytag.get(260,[])))
    # fallback year from field 18 if missing
    m=re.search(r'(18|19|20)\d{2}', year)
    year=m.group(0) if m else year
    isbn=[]
    for tag in (20, 24):
        for f in bytag.get(tag,[]):
            val=normalize_isbn(sf_text(f,'a'))
            if val and val not in isbn: isbn.append(val)
    physical=clean(' '.join(sf_text(f,'a') + (' ' + sf_text(f,'b') if sf_text(f,'b') else '') for f in bytag.get(300,[])))
    subjects=[]
    for tag in (600,610,611,630,650,651,653,659):
        for f in bytag.get(tag,[]):
            val=sf_text(f,'a')
            if val:
                val=clean(val)
                if val and val not in subjects: subjects.append(val)
    copies=[]
    for f in bytag.get(859,[]):
        sf=subfields(f)
        # sometimes one field contains one copy; keep known subfields
        copy={
          'inventario': first_nonempty(sf.get('a',[])),
          'sede': first_nonempty(sf.get('l',[])),
          'signatura': first_nonempty(sf.get('m',[])),
          'codigo_autor': first_nonempty(sf.get('n',[])),
          'prestamo': first_nonempty(sf.get('d',[])),
          'procedencia': first_nonempty(sf.get('g',[])),
        }
        if any(copy.values()): copies.append(copy)
    sede = first_nonempty([c.get('sede','') for c in copies]) or clean(' '.join(sf_text(f,'a') for f in bytag.get(852,[])))
    # fallback raw searchable text
    raw=' '.join(text for _,text in fields)
    if not title:
        # try to recover any 245 raw after ^a
        for f in bytag.get(245,[]):
            title=clean(re.sub(r'\^[a-z0-9]', ' ', strip_indicators(f)))
            if title: break
    if title or authors or isbn:
        books.append({
          'id': mfn,
          'mfn': mfn,
          'titulo': title,
          'autor': '; '.join(authors),
          'autores': authors,
          'responsabilidad': responsibility,
          'editorial': publisher,
          'lugar': place,
          'anio': year,
          'isbn': isbn[0] if isbn else '',
          'isbns': isbn,
          'edicion': edition,
          'descripcion': physical,
          'temas': subjects,
          'sede': sede,
          'ejemplares': copies,
          'disponible': True if copies else None,
          'texto_busqueda': clean(raw),
        })

OUT_JSON.write_text(json.dumps(books, ensure_ascii=False, indent=2), encoding='utf-8')
# JS with several compatible global names, harmless if the current site uses one of them
js = 'window.CATALOGO_AGUAPEY = ' + json.dumps(books, ensure_ascii=False, separators=(',',':')) + ';\n' + \
     'window.CATALOGO = window.CATALOGO_AGUAPEY;\n' + \
     'window.catalogo = window.CATALOGO_AGUAPEY;\n' + \
     'window.books = window.CATALOGO_AGUAPEY;\n'
OUT_JS.write_text(js, encoding='utf-8')
print(json.dumps({
 'nxtmfn': nxt,
 'registros_detectados': len(latest),
 'libros_exportados': len(books),
 'con_isbn': sum(1 for x in books if x['isbn']),
 'con_ejemplares': sum(1 for x in books if x['ejemplares']),
 'json': str(OUT_JSON),
 'js': str(OUT_JS),
 'primeros': books[:3]
}, ensure_ascii=False, indent=2))
