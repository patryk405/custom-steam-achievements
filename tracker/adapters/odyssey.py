"""Bounded read-only SMO File1.bin BYML v3 reader.
Format reference: Alex Norum's MIT mario_odyssey_save_editor (see licenses/).
No game files are modified. Only the explicitly selected slot is read.
"""
import struct
from .bbport import bounded


def parse(raw):
    data = raw[16:]
    if data[:4] != b'YB\x03\x00':
        raise ValueError('Expected Odyssey save with BYML v3 at offset 16')
    budget = 200000
    active = set()
    def take(off, size):
        if off < 0 or size < 0 or off + size > len(data):
            raise ValueError('Truncated BYML')
        return data[off:off+size]
    def u32(off):
        return int.from_bytes(take(off, 4), 'little')
    def header(off, kind):
        value = u32(off)
        if value & 255 != kind or value >> 8 > 50000:
            raise ValueError('Invalid BYML node')
        return value >> 8
    def strings(off):
        if not off: return []
        count = header(off, 0xc2)
        result = []
        for i in range(count):
            pos = off + u32(off+4+i*4)
            take(pos, 1)
            end = data.find(b'\0', pos, min(pos+4097,len(data)))
            if end < 0: raise ValueError('Invalid BYML string')
            result.append(data[pos:end].decode('utf-8'))
        return result
    keys, texts = strings(u32(4)), strings(u32(8))
    def value(kind, off, depth):
        nonlocal budget
        budget -= 1
        if budget < 0 or depth > 32: raise ValueError('BYML limits exceeded')
        val = u32(off)
        if kind == 0xff: return None
        if kind == 0xd0:
            if val not in (0,1): raise ValueError('Invalid boolean')
            return bool(val)
        if kind == 0xd1: return struct.unpack('<i',take(off,4))[0]
        if kind == 0xd3: return val
        if kind == 0xd2: return struct.unpack('<f',take(off,4))[0]
        if kind == 0xa0:
            if val >= len(texts): raise ValueError('Invalid string index')
            return texts[val]
        if kind in (0xc0,0xc1): return node(val,kind,depth+1)
        if kind in (0xd4,0xd5,0xd6):
            return struct.unpack({0xd4:'<q',0xd5:'<Q',0xd6:'<d'}[kind],take(val,8))[0]
        raise ValueError('Unsupported BYML type')
    def node(off,kind,depth):
        if off in active: raise ValueError('Cyclic BYML')
        active.add(off)
        n = header(off,kind)
        if kind == 0xc0:
            start = off+4+((n+3)&~3)
            take(start,n*4)
            result = [value(take(off+4+i,1)[0],start+i*4,depth) for i in range(n)]
        else:
            result = {}
            take(off+4,n*8)
            for i in range(n):
                entry = off+4+i*8
                tag = u32(entry); key = tag & 0xffffff
                if key >= len(keys) or keys[key] in result: raise ValueError('Invalid or duplicate key')
                result[keys[key]] = value(tag>>24,entry+4,depth)
        active.remove(off)
        return result
    return node(u32(12),0xc1,0)


def extract(root):
    if not isinstance(root,dict) or not all(k in root for k in ('WorldInfo','ShineData','GameProgressData')):
        raise ValueError('Not an Odyssey progress save')
    metrics = {}; total = 0; seen = set()
    for entry in root['WorldInfo']:
        uid = entry['UnlockedWorldId']; moons = entry['PayShineNum']
        if type(uid) is not int or not -1 <= uid <= 16 or type(moons) is not int or not 0 <= moons <= 999:
            raise ValueError('Invalid kingdom progress')
        if uid < 0: continue
        if uid in seen: raise ValueError('Duplicate kingdom')
        seen.add(uid)
        metrics[f'kingdom:{uid}'] = 1
        metrics[f'moons:{uid}'] = moons
        total += moons
    if total > 999: raise ValueError('Invalid moon total')
    metrics['moons'] = total
    return metrics


def read_metrics(path, manifest):
    return extract(parse(bounded(path)))
