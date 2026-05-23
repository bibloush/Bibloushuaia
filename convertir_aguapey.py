# -*- coding: utf-8 -*-
"""
Conversor básico Aguapey/CDS-ISIS MST -> JSON/CSV/HTML
Uso:
  1) Colocar este archivo en la misma carpeta que marc.mst
  2) Ejecutar: python convertir_aguapey.py
  3) Se generan: catalogo.json, catalogo.csv e index.html

Nota: este conversor está preparado para bases Aguapey/MARC similares a la analizada.
Trabaja sobre el archivo marc.mst y no modifica la base original.
"""

import struct, json, csv, re
from pathlib import Path
from collections import defaultdict, Counter

MST_PATH = Path("marc.mst")
OUT_JSON = Path("catalogo.json")
OUT_CSV = Path("catalogo.csv")
OUT_HTML = Path("index.html")

def parse_header(data, pos):
    if pos + 18 > len(data):
        return None
    b = data[pos:pos+18]
    mfn = struct.unpack("<I", b[0:4])[0]
    mfrl = struct.unpack("<I", b[4:8])[0]
    base = struct.unpack("<H", b[12:14])[0]
    nvf = struct.unpack("<H", b[14:16])[0]
    status = struct.unpack("<H", b[16:18])[0]
    return mfn, mfrl, base, nvf, status

def validate_record(data, pos):
    h = parse_header(data, pos)
    if not h:
        return False
    mfn, mfrl, base, nvf, status = h
    if not (1 <= mfn <= 100000 and 50 <= mfrl <= 20000 and 18 <= base < mfrl and 0 <= nvf <= 300):
        return False
    if base != 18 + nvf * 6:
        return False
    data_len = mfrl - base
    for i in range(nvf):
        off = pos + 18 + i * 6
        tag, start, length = struct.unpack("<HHH", data[off:off+6])
        if not (0 < tag < 2000 and 0 <= start <= data_len and 0 <= length <= data_len and start + length <= data_len):
            return False
    field_data = data[pos+base:pos+mfrl]
    if not field_data:
        return False
    printable = sum(32 <= b <= 255 or b in (9, 10, 13) for b in field_data) / len(field_data)
    return printable >= 0.8

def parse_record(data, pos):
    mfn, mfrl, base, nvf, status = parse_header(data, pos)
    data_start = pos + base
    fields = {}
    for i in range(nvf):
        off = pos + 18 + i * 6
        tag, start, length = struct.unpack("<HHH", data[off:off+6])
        raw = data[data_start+start:data_start+start+length]
        s = raw.decode("cp850", errors="replace")
        fields.setdefault(tag, []).append(s)
    return {"mfn": mfn, "pos": pos, "mfrl": mfrl, "fields": fields}

def parse_subfields(s):
    if "^" in s:
        indicators = s.split("^", 1)[0]
        rest = s[len(indicators):]
    else:
        rest = s
    d = defaultdict(list)
    for part in rest.split("^"):
        if not part:
            continue
        code = part[0]
        val = part[1:].strip()
        if val:
            d[code].append(val)
    return dict(d)

def all_sub(fields, tag, code="a"):
    vals = []
    for f in fields.get(tag, []):
        vals.extend(parse_subfields(f).get(code, []))
    return [v.strip() for v in vals if v.strip()]

def first_sub(fields, tag, code="a"):
    vals = all_sub(fields, tag, code)
    return vals[0] if vals else ""

def title_from(fields):
    for f in fields.get(245, []):
        d = parse_subfields(f)
        a = " ".join(d.get("a", [])).strip(" /:;")
        b = " ".join(d.get("b", [])).strip(" /:;")
        if a and b:
            return f"{a}: {b}"
        return a or b
    return ""

def authors_from(fields):
    vals = []
    for tag in [100, 110, 111, 700, 710, 711]:
        vals += all_sub(fields, tag, "a")
    out, seen = [], set()
    for v in vals:
        vv = re.sub(r"\s+", " ", v).strip(" /.;")
        key = vv.lower()
        if vv and key not in seen:
            seen.add(key)
            out.append(vv)
    return out

def subjects_from(fields):
    vals = []
    for tag in [600, 610, 611, 650, 651, 653, 659, 690]:
        for code in ["a", "b", "c", "x", "y", "z"]:
            vals += all_sub(fields, tag, code)
    out, seen = [], set()
    for v in vals:
        vv = re.sub(r"\s+", " ", v).strip(" /.;,")
        key = vv.lower()
        if vv and key not in seen:
            seen.add(key)
            out.append(vv)
    return out

def pub_year(fields):
    years = []
    for f in fields.get(260, []):
        for v in parse_subfields(f).get("c", []):
            years += re.findall(r"(1[5-9]\d{2}|20\d{2}|21\d{2})", v)
    if not years:
        for f in fields.get(18, []) + fields.get(8, []):
            years += re.findall(r"(1[5-9]\d{2}|20\d{2}|21\d{2})", f)
    return years[0] if years else ""

def holdings_from(fields):
    holdings = []
    for f in fields.get(859, []):
        d = parse_subfields(f)
        holdings.append({
            "inventario": (d.get("a") or [""])[0].strip(),
            "sede": (d.get("l") or [""])[0].strip(),
            "clasificacion": (d.get("m") or [""])[0].strip(),
            "signatura": (d.get("n") or [""])[0].strip(),
            "modalidad": (d.get("d") or [""])[0].strip(),
            "adquisicion": (d.get("g") or [""])[0].strip(),
        })
    return holdings

def convert():
    data = MST_PATH.read_bytes()
    valid = []
    for pos in range(64, len(data)-18):
        h = parse_header(data, pos)
        if not h:
            continue
        mfn, mfrl, base, nvf, status = h
        if 1 <= mfn <= 100000 and 50 <= mfrl <= 20000 and validate_record(data, pos):
            valid.append((mfn, pos))

    latest_positions = {}
    for mfn, pos in valid:
        if mfn not in latest_positions or pos > latest_positions[mfn]:
            latest_positions[mfn] = pos

    catalog = []
    for mfn, pos in sorted(latest_positions.items()):
        rec = parse_record(data, pos)
        fields = rec["fields"]
        holdings = holdings_from(fields)
        item = {
            "mfn": rec["mfn"],
            "numero_control": fields.get(1, [""])[0],
            "titulo": title_from(fields),
            "responsabilidad": first_sub(fields, 245, "c"),
            "autores": authors_from(fields),
            "lugar": first_sub(fields, 260, "a"),
            "editorial": first_sub(fields, 260, "b"),
            "anio": pub_year(fields),
            "isbn": first_sub(fields, 20, "a"),
            "descripcion_fisica": " ".join(all_sub(fields, 300, "a") + all_sub(fields, 300, "b")).strip(),
            "coleccion": first_sub(fields, 440, "a"),
            "idioma": first_sub(fields, 8, "a"),
            "temas": subjects_from(fields),
            "ejemplares": holdings,
            "inventarios": [h["inventario"] for h in holdings if h["inventario"]],
            "ubicaciones": [h["sede"] for h in holdings if h["sede"]],
            "signaturas": [(" ".join([h["clasificacion"], h["signatura"]])).strip() for h in holdings if h["clasificacion"] or h["signatura"]],
        }
        catalog.append(item)

    OUT_JSON.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")

    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "mfn", "numero_control", "titulo", "autores", "responsabilidad", "lugar", "editorial", "anio",
            "isbn", "descripcion_fisica", "coleccion", "idioma", "temas", "inventarios", "ubicaciones", "signaturas"
        ], delimiter=";")
        writer.writeheader()
        for i in catalog:
            writer.writerow({
                "mfn": i["mfn"],
                "numero_control": i["numero_control"],
                "titulo": i["titulo"],
                "autores": " | ".join(i["autores"]),
                "responsabilidad": i["responsabilidad"],
                "lugar": i["lugar"],
                "editorial": i["editorial"],
                "anio": i["anio"],
                "isbn": i["isbn"],
                "descripcion_fisica": i["descripcion_fisica"],
                "coleccion": i["coleccion"],
                "idioma": i["idioma"],
                "temas": " | ".join(i["temas"]),
                "inventarios": " | ".join(i["inventarios"]),
                "ubicaciones": " | ".join(i["ubicaciones"]),
                "signaturas": " | ".join(i["signaturas"]),
            })

    print(f"Conversión terminada: {len(catalog)} registros")
    print(f"Archivos generados: {OUT_JSON}, {OUT_CSV}")

if __name__ == "__main__":
    if not MST_PATH.exists():
        print("No encuentro marc.mst en esta carpeta.")
    else:
        convert()
