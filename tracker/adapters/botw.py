"""Read-only BOTW flag-save adapter. Format verified against the user's 1.9 Bootup schema.
References: Marc Robledo's save editor and SavageWind's documented save format.
"""
import struct
import zlib

def read_flags(data, versions, expected_size=True):
    if len(data) < 16 or len(data) > 2_000_000 or data[-4:] != b'\xff'*4 or (len(data)-16) % 8:
        raise ValueError('Incomplete or invalid BOTW save')
    revision = struct.unpack_from('<I', data)[0]
    if str(revision) not in versions:
        raise ValueError('Unsupported save revision: ' + hex(revision))
    if expected_size and len(data) != versions[str(revision)]:
        raise ValueError('Unexpected save length for this revision')
    result, last = {}, -1
    for offset in range(12, len(data)-4, 8):
        key, value = struct.unpack_from('<II', data, offset)
        if key < last:
            raise ValueError('Unsorted save entries')
        result.setdefault(key, []).append(value)
        last = key
    return result

def read_metrics(path, manifest):
    raw = read_flags(path.read_bytes(), manifest['versions'])
    caption_path = path.with_name('caption.sav')
    caption = read_flags(caption_path.read_bytes(), manifest['versions'], False) if caption_path.is_file() else {}
    result = {}
    for rule in manifest['rules'].values():
        for key in rule['flags']:
            name = key.removeprefix('caption:')
            source = caption if key.startswith('caption:') else raw
            values = source.get(zlib.crc32(name.encode()))
            if values is not None and len(values) == 1:
                result[key] = values[0]
    return result
