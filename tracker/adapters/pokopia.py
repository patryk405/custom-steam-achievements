"""Read-only Pokopia 2.0.1 CMNDAT.BIN parser. No mod, journal or game writes.
Format/offsets adapted from berichan/PokoHex at 2de3651266877bb0d765e4b5cd273dc7e2e36f96.
GPL-3.0; see licenses/PokoHex-GPL-3.0.txt. Public numeric IDs in resources/pokopia-layout.json.
"""
import json
import struct
import zlib
from pathlib import Path
from platform_support import resource_directory
from .bbport import bounded

SIZE = 0x470CED
HEADER = 0x130
LAYOUT = json.loads((resource_directory()/'resources/pokopia-layout.json').read_text())


def parse(raw):
    if len(raw) < HEADER:
        raise ValueError('Truncated Pokopia save')
    magic, revision, kind = struct.unpack_from('<III', raw)
    if (magic, revision, kind) != (0x31227687, 0x0200017D, 0x40001):
        raise ValueError('Only Pokopia 2.0.1 CMNDAT.BIN is supported')
    length = struct.unpack_from('<I',raw,0x10)[0]
    if not HEADER < length <= len(raw):
        raise ValueError('Invalid compressed save length')
    decoder = zlib.decompressobj()
    data = decoder.decompress(raw[HEADER:length], SIZE+1)
    if len(data) != SIZE or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
        raise ValueError('Incomplete or unsupported Pokopia save payload')
    return data


def metrics(data):
    if len(data) != SIZE: raise ValueError('Invalid Pokopia layout')
    result = {
        'dex':sum((data[0x426EFF+i]&3)==3 for i in LAYOUT['dex']),
        'habitats':sum(bool(data[0x4256FF+i*12]&2) for i in LAYOUT['habitats']),
        'recipes':sum(bool(data[0x3FCB4C+i*6+4]&2) for i in LAYOUT['recipes']),
        'water_gun_uses':struct.unpack_from('<I',data,0x405047+3*8)[0],
    }
    flags=data[0x220F04:0x220F04+32]
    result['moves']=sum(bool(data[0x405047+i*8+4]&1) and (i!=10 or bool(flags[7]&1)) and (i!=11 or bool(flags[7]&2)) for i in (1,2,3,4,5,6,10,11,12,13))
    return result


def read_metrics(path, manifest):
    # Recompia uses a sibling .commit marker during save transactions. Wait until
    # it finishes even if the compressed file happens to look complete already.
    account=path.parent.parent
    if account.with_name(account.name+'.commit').exists():
        raise ValueError('Waiting for Pokopia save transaction to finish')
    return metrics(parse(bounded(path)))
