"""Reviewed source-specific display overlays. No writers or canonical consumers.

Rules bind immutable workbook bytes and a particular profile/sheet. Their ranges
were verified against the original workbook, including merged/subheader cells.
Changing source bytes requires a new review, never a fuzzy match or fallback.
"""
from datetime import date
import math
import re

VERSION = 'SOURCE_INTERPRETATION_05_V1'
FAN_SHA = '38097314ad0bf64cfca3fe5fdd2cad509b8eadda78b7706dbcd07daa571f3c64'
BC_SHA = 'b89e8bb2ee047ec0e7805af048b82b3553ec427f038a97797400721e1ee61bf1'


def rule(row):
    if row['axis'] != 'ROW' or row['kind'] != 'MEASUREMENT_SOURCE':
        return None
    key = (row['source_sha'], row['source_ref'], row['sheet_index'], row['profile_id'])
    if key == (FAN_SHA, 'WB-FAN', 0, 'wb-fan-s001-b01'):
        return 'FAN'
    if key == (BC_SHA, 'WB-VIB-BC', 2, 'wb-vib-bc-s003-b01'):
        return 'BC43'
    return None


def requested_cells(row):
    """Fixed bounded context only; called after the existing authorized lookup."""
    selected = rule(row)
    if selected == 'FAN':
        return {'G7', 'G8', 'H8', 'J7', 'J8', 'F7',
                *[f'{c}{r}' for c in 'KLMNOPQR' for r in (8, 9)]}
    if selected == 'BC43':
        return {'A1', 'B1', f"A{row['position']}",
                *[f'{c}2' for c in 'BCDEFGHIJKLMNOPQRSTUVWXYZ'], 'AA2'}
    return set()


def date_claim(proof):
    if not proof or proof.get('formula_present') or proof.get('source_type') not in ('n', 's'):
        return None
    raw = proof.get('raw_value')
    if type(raw) not in (int, str) or not re.fullmatch(r'[0-9]{8}', str(raw)):
        return None
    text = str(raw)
    try:
        result = date(int(text[:4]), int(text[4:6]), int(text[6:]))
    except ValueError:
        return None
    return result if 1970 <= result.year <= 2100 else None


def literal(proof, expected):
    return proof is not None and not proof.get('formula_present') and proof.get('raw_value') == expected


def proof_ref(cells, address):
    return {'coordinate': address, **cells.get(address, {'raw_value': None, 'presence': 'NO_POPULATED_CELL_IN_COMPLETE_SOURCE_CENSUS'})}


def interpret(row, fields, cells, anchors=()):
    """Return separate derived claims; never modify row, fields or cell proofs."""
    selected = rule(row)
    if not selected:
        return None
    result = {'version': VERSION, 'canonical_eligible': False, 'persisted': False,
              'source_sha256': row['source_sha'], 'fields': [], 'date': None,
              'row_context': None, 'notice': 'Interpretasi sumber untuk ditinjau; bukan pengesahan engineer atau hubungan aset kanonis.'}

    def claim(field, label, unit, refs, kind='SOURCE_HEADER', note=None):
        return {'field_id': field['field_id'], 'cell': field['cell'], 'kind': kind,
                'label': label, 'unit': unit, 'method': 'EXACT_REVIEWED_SOURCE_HEADERS',
                'evidence': [proof_ref(cells, a) for a in refs], 'note': note}

    if selected == 'FAN':
        if row['position'] in (8, 9) and literal(cells.get('J8'), '(ppm)') and literal(cells.get('G8'), 'Viscosity (Cst)'):
            result['row_context'] = {'label': 'KONTEKS HEADER', 'method': 'REVIEWED_SUBHEADER_ROWS_8_9',
                'evidence': [proof_ref(cells, a) for a in ('G8', 'J8')],
                'note': 'Baris subheader pada workbook; jangan isi tanggal atau nilai ukur yang kosong. Klasifikasi impor asli dipertahankan.'}
            return result
        if row['position'] < 10:
            return None
        for field in fields:
            match = re.fullmatch(r'([A-Z]+)([0-9]+)', field['cell'])
            if not match or int(match[2]) != row['position']:
                continue
            col = match[1]
            if col == 'J' and literal(cells.get('J7'), 'Ferrous') and literal(cells.get('J8'), '(ppm)'):
                result['fields'].append(claim(field, 'Ferrous', 'ppm', ['J7', 'J8']))
            elif col in 'KLMNOPQR' and len(col) == 1 and literal(cells.get(col+'9'), '(ppm)') and isinstance(cells.get(col+'8', {}).get('raw_value'), str):
                result['fields'].append(claim(field, cells[col+'8']['raw_value'], 'ppm', [col+'8', col+'9']))
            elif col == 'G' and literal(cells.get('G8'), 'Viscosity (Cst)'):
                result['fields'].append(claim(field, 'Viscosity', 'Cst', ['G7', 'G8'], note='Unit sumber Cst dipertahankan; heading (%) di G7 tidak diterapkan ke kolom G. Klaim profil lama tetap terlihat.'))
            elif col == 'H' and literal(cells.get('G7'), ' Viscosity Change\n(%)') and literal(cells.get('H8'), 'Result'):
                result['fields'].append(claim(field, 'Result — Viscosity Change', '%', ['G7', 'H8'], note='Klaim heading sumber; hasil rumus/cache tetap referensi yang belum disahkan dan tidak dihitung ulang.'))
        return result

    if not literal(cells.get('A1'), 'TANGGAL') or not literal(cells.get('B1'), 'BC 43 - mm/s'):
        return None
    clock_address = f"A{row['position']}"
    parsed = date_claim(cells.get(clock_address))
    if parsed:
        result['date'] = {'value': parsed.isoformat(), 'precision': 'DATE', 'role': 'UNSPECIFIED',
            'method': 'YYYYMMDD_SOURCE_DATE', 'evidence': [proof_ref(cells, a) for a in ('A1', clock_address)],
            'note': 'Tanggal sumber saja; bukan measured_at, tanpa jam atau zona rekaan.'}
    for field in fields:
        match = re.fullmatch(r'([A-Z]+)([0-9]+)', field['cell'])
        if not match or int(match[2]) != row['position']:
            continue
        col = match[1]; point = cells.get(col+'2', {})
        if not re.fullmatch(r'[1-9][0-9]*[VHA]', str(point.get('raw_value', ''))) or point.get('formula_present'):
            continue
        item = claim(field, point['raw_value'], 'mm/s', ['B1', col+'2'], note='Header B1:AA1 mencakup blok ini; label aset sumber BC 43 belum merupakan mapping aset aplikasi.')
        # One reviewed gap only. No generic blank filling or extrapolation.
        if (row['position'], field['cell'], field['field_id']) == (23, 'L23', 'field-l2') and parsed == date(2021, 5, 20) and literal(point, '4H'):
            estimate = estimate_gap(row, field, cells, anchors, parsed)
            if estimate:
                item['estimate'] = estimate
        result['fields'].append(item)
    return result


def estimate_gap(row, field, cells, anchors, target_date):
    target = field['value']
    if field.get('role') != 'INPUT' or target.get('raw_value') is not None or target.get('formula_present'):
        return None
    expected = {22: ('A22', 'L22'), 24: ('A24', 'L24')}
    if len(anchors) != 2 or {a['position'] for a in anchors} != set(expected):
        return None
    for anchor in anchors:
        if any(anchor[k] != row[k] for k in ('source_sha', 'source_ref', 'sheet_index', 'profile_id', 'profile_hash', 'owner_id', 'access_asset_id')):
            return None
        if anchor['axis'] != 'ROW' or anchor['kind'] != 'MEASUREMENT_SOURCE':
            return None
        address = expected[anchor['position']][1]
        if not any(f['cell'] == address and f['field_id'] == 'field-l2' and f['role'] == 'INPUT' for f in anchor['document']['fields']):
            return None
    dates = [date_claim(cells.get(a)) for a in ('A22', 'A24')]
    values = [cells.get(a, {}) for a in ('L22', 'L24')]
    if any(v.get('formula_present') or type(v.get('raw_value')) not in (int, float) or not math.isfinite(v['raw_value']) for v in values):
        return None
    if dates != [date(2021, 4, 21), date(2021, 6, 17)]:
        return None
    before, after = [v['raw_value'] for v in values]
    value = before + (after - before) * (target_date-dates[0]).days / (dates[1]-dates[0]).days
    if not math.isfinite(value):
        return None
    return {'label': 'ESTIMASI', 'value': value, 'unit': 'mm/s', 'confidence': 'LOW',
            'method': 'LINEAR_TIME_INTERPOLATION_DISPLAY_ONLY_V1', 'gap_days': 57,
            'evidence': [proof_ref(cells, a) for a in ('A22', 'L22', 'A23', 'A24', 'L24')],
            'notice': 'Perkiraan rendah keyakinan: asumsi perubahan linier selama 57 hari. Kondisi operasi/perawatan tidak diketahui. Hanya ilustrasi, bukan nilai terukur, kondisi mesin atau dasar alert/Case.'}
