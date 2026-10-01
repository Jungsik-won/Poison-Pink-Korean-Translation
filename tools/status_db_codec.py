#!/usr/bin/env python3
"""Sequential STATUS DB wire codec. Layout evidence: docs/STATUS_DB_FORMAT.md.

Numeric names describe wire positions, not speculative gameplay meanings.
Keep every on-disk bit, including bytes discarded by the native loader.
Text values are bytes: CP932 is only an inspection view, never the serializer.
"""
import copy
import hashlib
import struct


def numbers(prefix, kinds):
    return [(prefix + str(i), kind, None) for i, kind in enumerate(kinds)]


def text_field(name, capacity):
    return (name, 'z', capacity)


ID = [('id', 'H', None)]
# Text capacities include NUL and stop before the first live neighboring byte.
ITEM_NAME = [text_field('name', 19)]
DESCRIPTION = [text_field('description', 128)]
SCHEMAS = {
    'PPITEM': [
        ID + numbers('header_', 'BB') + ITEM_NAME + numbers('stats_', 'BBBBHHHHHHBBBH') + DESCRIPTION,
        ID + numbers('header_', 'B') + ITEM_NAME + numbers('stats_', 'BBB' + 'H' * 7 + 'B' + 'H' * 5) + DESCRIPTION,
        ID + numbers('header_', 'B') + ITEM_NAME + numbers('stats_', 'BBB' + 'H' * 21) + DESCRIPTION,
        ID + numbers('header_', 'B') + ITEM_NAME + numbers('stats_', 'BHBHH') + DESCRIPTION,
        numbers('value_', 'BBHH'),
    ],
    'PPSKILL': [
        ID + numbers('header_', 'HH') + [text_field('name', 17)]
        # Bytes 15 and 19 after name NUL are skipped by the game, but preserved here.
        + numbers('stats_', 'BBB' + 'H' * 5 + 'BBBBBBBB' + 'H' * 19 + 'BHHH') + DESCRIPTION,
    ],
    'PPPARAM': [
        ID + numbers('header_', 'H') + [text_field('name', 19)]
        # u16 cells read only as low bytes remain full u16 wire values.
        + numbers('stats_', 'BBBBBB' + 'H' * 6 + 'BBHBBHHH' + 'HHH' + 'BH' * 6 + 'H'),
        ID + [text_field('name_0', 21)] + numbers('pair_0_', 'BBHHHH')
        + [text_field('name_1', 21)] + numbers('pair_1_', 'BBHHHH') + numbers('tail_', 'HHHH'),
        ID + [('entry_count', 'B', None)],  # variable entries appended below
        numbers('group_', 'B' * 18) + numbers('value_', 'H' * 6),
        ID + sum(([('tag_' + str(i), 'B', None), text_field('name_' + str(i), 19)] for i in range(3)), []),
        ID + numbers('header_', 'HIIHBHH') + [text_field('description', 256)],
        ID + numbers('value_', 'HHHH'),
    ],
}
# Only the first PPPARAM variable table and the fixed 600B in-memory table
# have loader-derived count limits beyond the uint16 wire count.
SECTION_LIMITS = {('PPPARAM', 3): 25}
LOADER_VAS = {
    'PPITEM': [0x275118, 0x275550, 0x2758b8, 0x275ba0, 0x275e08],
    'PPSKILL': [0x276af0],
    'PPPARAM': [0x26c2e0, 0x26ca18, 0x26ccd0, 0x26cef0, 0x26d110, 0x26d2c8, 0x26d568],
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def extra_schema(kind, section, fields):
    if (kind, section) != ('PPPARAM', 2):
        return []
    count = fields[-1]['value']
    if not 0 <= count <= 15:
        raise ValueError('PPPARAM section 2 exceeds 15 in-memory entries')
    return sum((numbers('entry_%d_' % i, 'BBHH') for i in range(count)), [])


class Reader:
    def __init__(self, data):
        self.data, self.pos = data, 0

    def field(self, spec):
        name, kind, capacity = spec
        start = self.pos
        if kind == 'z':
            end = self.data.find(b'\0', start, start + capacity)
            if end < 0:
                raise ValueError('Unterminated/oversized %s at 0x%x (capacity %d)' % (name, start, capacity))
            value = self.data[start:end]
            self.pos = end + 1
        else:
            size = struct.calcsize('<' + kind)
            if self.pos + size > len(self.data):
                raise ValueError('Truncated %s at 0x%x' % (name, start))
            value = struct.unpack_from('<' + kind, self.data, self.pos)[0]
            self.pos += size
        return dict(name=name, type=kind, value=value, offset=start, size=self.pos-start)


def parse(data, kind):
    if kind not in SCHEMAS:
        raise ValueError('Unsupported DB: ' + str(kind))
    reader = Reader(data)
    sections = []
    for index, schema in enumerate(SCHEMAS[kind]):
        start = reader.pos
        count = reader.field(('count', 'H', None))['value']
        if count > SECTION_LIMITS.get((kind, index), 65535):
            raise ValueError('Section count exceeds native allocation')
        rows, seen = [], set()
        for row_index in range(count):
            row_start = reader.pos
            fields = [reader.field(s) for s in schema]
            fields.extend(reader.field(s) for s in extra_schema(kind, index, fields))
            if fields[0]['name'] == 'id':
                row_id = fields[0]['value']
                if row_id in seen:
                    raise ValueError('Duplicate ID %d in section %d' % (row_id, index))
                seen.add(row_id)
            rows.append(dict(index=row_index, offset=row_start, size=reader.pos-row_start, fields=fields))
        sections.append(dict(index=index, offset=start, size=reader.pos-start, count=count, records=rows))
    if reader.pos != len(data):
        raise ValueError('Unconsumed bytes at 0x%x: %d' % (reader.pos, len(data)-reader.pos))
    return dict(kind=kind, size=len(data), source_sha256=digest(data), sections=sections)


def serialize(model):
    kind = model['kind']
    if kind not in SCHEMAS or len(model['sections']) != len(SCHEMAS[kind]):
        raise ValueError('Invalid DB schema/sections')
    out = bytearray()
    for index, (section, base_schema) in enumerate(zip(model['sections'], SCHEMAS[kind])):
        rows = section['records']
        if section['index'] != index or section['count'] != len(rows) or len(rows) > 65535:
            raise ValueError('Section index/count mismatch')
        out += struct.pack('<H', len(rows))
        for row_index, row in enumerate(rows):
            fields = row['fields']
            if row['index'] != row_index or len(fields) < len(base_schema):
                raise ValueError('Record index/fields mismatch')
            schema = base_schema + extra_schema(kind, index, fields[:len(base_schema)])
            if len(fields) != len(schema):
                raise ValueError('Unexpected or missing fields')
            for field, (name, ftype, capacity) in zip(fields, schema):
                if (field['name'], field['type']) != (name, ftype):
                    raise ValueError('Field schema mismatch')
                value = field['value']
                if ftype == 'z':
                    if not isinstance(value, bytes) or b'\0' in value or len(value) >= capacity:
                        raise ValueError('Invalid text bytes/capacity: ' + name)
                    out += value + b'\0'
                else:
                    if type(value) is not int or not 0 <= value < (1 << (8 * struct.calcsize('<' + ftype))):
                        raise ValueError('Invalid numeric field: ' + name)
                    out += struct.pack('<' + ftype, value)
    result = bytes(out)
    parse(result, kind)  # count limits, ID uniqueness, exact EOF
    return result


def nontext_signature(model):
    return [(s['index'], s['count'], [[(f['name'], f['type'], f['value']) for f in r['fields']
                                     if f['type'] != 'z'] for r in s['records']]) for s in model['sections']]


def text_fields(model):
    for s in model['sections']:
        for r in s['records']:
            for f in r['fields']:
                if f['type'] == 'z':
                    yield (s['index'], r['index'], f['name']), f


def replace_text(data, kind, replacements, expected_sha256):
    """Offline experiment only. Keys=(section,index,field); values=(old,new) bytes.

    Enforces source identity, native buffer bounds, strict CP932 and nontext
    invariance. Game glyph mapping, UI fit and runtime safety are separate gates.
    """
    if digest(data) != expected_sha256:
        raise ValueError('Source hash mismatch')
    before = parse(data, kind)
    after = copy.deepcopy(before)
    editable = dict(text_fields(after))
    for key, (old, new) in replacements.items():
        if key not in editable or editable[key]['value'] != old:
            raise ValueError('Unknown text location or source text mismatch: ' + str(key))
        if not isinstance(new, bytes):
            raise ValueError('Replacement must be game-encoded bytes')
        new.decode('cp932', errors='strict')
        editable[key]['value'] = new
    result = serialize(after)
    checked = parse(result, kind)
    if nontext_signature(before) != nontext_signature(checked):
        raise ValueError('Nontext fields changed')
    original_text = dict(text_fields(before))
    for key, field in text_fields(checked):
        expected = replacements[key][1] if key in replacements else original_text[key]['value']
        if field['value'] != expected:
            raise ValueError('Unintended text change')
    return result
