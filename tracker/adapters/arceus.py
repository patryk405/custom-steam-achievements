"""Read-only PLA Swish save decoder, derived from PKHeX (GPL-3.0).
See licenses/PKHeX-GPL-3.0.txt and THIRD-PARTY.md. No keys or game ROM needed.
"""
import hashlib
import struct
from .bbport import bounded
IntroHashBytes = bytes.fromhex('9ec99cd70ed33c44fb9303dceb39b42a1947e9634ba2334416bf82a2ba6355b63d9df24b5f7b6ab2621dc21b68e5c8b53a059000e8a8103de2ecf00cb2ed4f6d')
OutroHashBytes = bytes.fromhex('d6c01c598bc8b8cb46e153fc828c757513e045df32693c75f059f8d9a25fb217e08052dbea8973997579afcb2e8007e6f126e0030ae66ff641bf7e59c2ae55fd')
StaticXorpad = bytes.fromhex('a092d10607db32a1ae01f5c51e844fe353ca37f4a7b04da018b7c297da5f532b75fa4816f8d48a6f6105f4e2fd04b5a30ffc4492cb32e61bb9b12e01b0565336d2d1503dde5b2e0e52fddf2f7bca6350a4675d2317c052e1a6307c2bb670365b2a276933f5637b363f269ba3ed7a5300a448b3509e14a052de7e102b1b776e')

SIZES = {3:1,8:1,9:2,10:4,11:8,12:1,13:2,14:4,15:8,16:4,17:8}

class Stream:
    def __init__(self, seed):
        self.state = seed
        self.offset = 0
        for _ in range(seed.bit_count()): self.advance()
    def advance(self):
        s = self.state
        s ^= (s << 2) & 0xffffffff
        s ^= s >> 15
        s ^= (s << 13) & 0xffffffff
        self.state = s
    def next(self):
        result = (self.state >> (8*self.offset)) & 255
        self.offset += 1
        if self.offset == 4:
            self.offset = 0
            self.advance()
        return result


def decode(raw, wanted):
    if len(raw) < 37 or hashlib.sha256(IntroHashBytes+raw[:-32]+OutroHashBytes).digest() != raw[-32:]:
        raise ValueError('Arceus save checksum mismatch; waiting for a complete save')
    data = bytes(b ^ StaticXorpad[i % 127] for i,b in enumerate(raw[:-32]))
    pos = 0; result = {}; seen = set()
    while pos < len(data):
        if len(seen) > 100000 or pos+5 > len(data): raise ValueError('Invalid save block')
        key = int.from_bytes(data[pos:pos+4],'little'); pos += 4
        if key in seen: raise ValueError('Duplicate save block')
        seen.add(key); rng = Stream(key)
        def read(n):
            nonlocal pos
            if n < 0 or pos+n > len(data): raise ValueError('Truncated save block')
            out = bytes(data[i] ^ rng.next() for i in range(pos,pos+n))
            pos += n
            return out
        kind = read(1)[0]
        if kind in (1,2):
            value = int(kind == 2)
        elif kind in (4,5):
            size = int.from_bytes(read(4),'little')
            if kind == 5:
                subtype = read(1)[0]
                if subtype not in SIZES: raise ValueError('Invalid array type')
                size *= SIZES[subtype]
            # Unrequested object data does not need to be decoded.
            if size > len(data)-pos: raise ValueError('Truncated save object')
            pos += size
            value = None
        elif kind in SIZES and kind != 3:
            payload = read(SIZES[kind])
            value = int.from_bytes(payload,'little') if kind in (8,9,10,11) else None
        else: raise ValueError('Invalid save block type')
        text = f'{key:08X}'
        if text in wanted:
            spec = wanted[text]
            expected = spec['type']
            if (expected == 'bool' and kind not in (1,2)) or (expected == 'u32' and kind != 10):
                raise ValueError('Unexpected Arceus metric type')
            if value is None or not 0 <= value <= spec['max']:
                raise ValueError('Invalid Arceus metric value')
            result['block:'+text] = value
    # Distinguish PLA from other Switch saves using PLA-specific structural keys.
    if not {0x02168706,0xF25C070E,0x50FE632A}.issubset(seen):
        raise ValueError('Save is not a supported Legends: Arceus save')
    return result


def read_metrics(path, manifest):
    return decode(bounded(path), manifest['blocks'])
