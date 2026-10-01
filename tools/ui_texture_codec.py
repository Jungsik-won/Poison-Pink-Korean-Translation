#!/usr/bin/env python3
"""Bounded codec for this game's observed single-picture indexed TIM2 assets.

Raw GS alpha and duplicate palette entries survive serialization. PNG previews
are inspection views, never the source of a lossless round trip.
"""
import hashlib
import struct


def sha(data):
    return hashlib.sha256(data).hexdigest()


def palette_slot(index, bpp, linear=False):
    if bpp == 4 or linear:
        return index
    return (index & ~24) | ((index & 8) << 1) | ((index & 16) >> 1)


def parse(data):
    if len(data) < 64 or data[:8] != b'TIM2\x04\x00\x01\x00':
        raise ValueError('Unsupported TIM2 magic/version/alignment/picture count')
    total, clut_size, image_size, header_size, colors = struct.unpack_from('<IIIHH', data, 16)
    width, height = struct.unpack_from('<HH', data, 36)
    if data[32:34] != b'\x00\x01' or data[34] not in (3, 0x83) or data[35] not in (4, 5):
        raise ValueError('Unsupported format/mipmaps/CLUT/image type')
    bpp = 4 if data[35] == 4 else 8
    if not width or not height or width * height % 2:
        raise ValueError('Unsupported dimensions')
    if header_size != 48 or colors != 1 << bpp or clut_size != colors * 4:
        raise ValueError('Unexpected picture header or palette size')
    if image_size != width * height * bpp // 8 or total != 48 + image_size + clut_size or len(data) != total + 16:
        raise ValueError('Truncated, padded, or inconsistent picture sizes')
    tex0 = struct.unpack_from('<Q', data, 40)[0]
    if (tex0 >> 20) & 63 != (20 if bpp == 4 else 19):
        raise ValueError('Unexpected GS pixel storage mode')
    indices = data[64:64 + image_size]
    raw_clut = data[64 + image_size:]
    linear = bool(data[34] & 0x80)
    palette = [raw_clut[palette_slot(i, bpp, linear)*4:palette_slot(i, bpp, linear)*4+4] for i in range(colors)]
    return dict(width=width, height=height, bpp=bpp, header=data[:64],
                clut_storage='linear' if linear else 'permuted',
                indices=indices, palette=palette, source_sha256=sha(data))


def serialize(model):
    raw_clut = bytearray(len(model['palette']) * 4)
    for i, color in enumerate(model['palette']):
        if len(color) != 4:
            raise ValueError('Palette entry must retain four raw bytes')
        start = palette_slot(i, model['bpp'], bool(model['header'][34] & 0x80)) * 4
        raw_clut[start:start+4] = color
    data = model['header'] + bytes(model['indices']) + bytes(raw_clut)
    check = parse(data)
    if any(check[k] != model[k] for k in ('width', 'height', 'bpp')):
        raise ValueError('Model/header mismatch')
    return data


def unpack_indices(model):
    if model['bpp'] == 8:
        return model['indices']
    return bytes(n for b in model['indices'] for n in (b & 15, b >> 4))


def preview_rgba(model):
    colors = [bytes((c[0], c[1], c[2], min(c[3] * 2, 255))) for c in model['palette']]
    return b''.join(colors[i] for i in unpack_indices(model))


def rect_indices(model, rect):
    x, y, w, h = rect
    if any(type(v) is not int for v in rect) or min(x, y) < 0 or min(w, h) <= 0 or x+w > model['width'] or y+h > model['height']:
        raise ValueError('Rectangle outside texture')
    pixels = unpack_indices(model)
    return b''.join(pixels[r*model['width']+x:r*model['width']+x+w] for r in range(y, y+h))


def replace_rect(data, rect, new_indices, expected_sha256, expected_rect_sha256):
    if sha(data) != expected_sha256:
        raise ValueError('Source texture changed')
    model = parse(data)
    old = rect_indices(model, rect)
    if sha(old) != expected_rect_sha256 or len(new_indices) != len(old):
        raise ValueError('Source rectangle or replacement size mismatch')
    if any(i >= len(model['palette']) for i in new_indices):
        raise ValueError('Index outside original palette')
    x, y, w, h = rect
    pixels = bytearray(unpack_indices(model))
    for row in range(h):
        off = (y+row)*model['width']+x
        pixels[off:off+w] = new_indices[row*w:(row+1)*w]
    if model['bpp'] == 8:
        model['indices'] = bytes(pixels)
    else:
        model['indices'] = bytes(pixels[i] | pixels[i+1] << 4 for i in range(0, len(pixels), 2))
    return serialize(model)


def uad_rectangles(data, width, height):
    """Read observed BE sprite rectangles; retain unparsed tail in source file."""
    if len(data) < 16 or data[:4] != b'UAD\0':
        raise ValueError('Unsupported UAD')
    count, tail_count, tail_start, total = struct.unpack_from('>4H', data, 4)
    if tail_start != 16 + count*32 or total != len(data) or tail_start > len(data):
        raise ValueError('Inconsistent UAD offsets/count/length')
    rows = []
    for i in range(count):
        x, y, w, h, cx, cy = struct.unpack_from('>6H', data, 16+i*32)
        if not w or not h or x+w > width or y+h > height:
            raise ValueError('UAD rectangle outside texture')
        rows.append(dict(index=i, rect=[x,y,w,h], anchor=[cx,cy],
                         raw_hex=data[16+i*32:48+i*32].hex()))
    return dict(rectangles=rows, tail_start=tail_start, tail_count_uninterpreted=tail_count,
                tail_sha256=sha(data[tail_start:]), source_sha256=sha(data))
