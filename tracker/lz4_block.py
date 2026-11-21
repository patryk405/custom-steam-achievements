"""Bounded raw LZ4 block decoder for validated NSO text (no external DLL)."""
def decompress(data, size):
    if not 0<size<=64*1024*1024:raise ValueError('Invalid LZ4 output size')
    out=bytearray();i=0
    def length(base):
        nonlocal i
        value=base
        if base==15:
            while True:
                if i>=len(data):raise ValueError('Truncated LZ4 length')
                extra=data[i];i+=1;value+=extra
                if value>size:raise ValueError('LZ4 length exceeds output')
                if extra!=255:break
        return value
    while i<len(data):
        token=data[i];i+=1;n=length(token>>4)
        if i+n>len(data) or len(out)+n>size:raise ValueError('Invalid LZ4 literals')
        out.extend(data[i:i+n]);i+=n
        if i==len(data):break
        if i+2>len(data):raise ValueError('Truncated LZ4 offset')
        offset=data[i]|data[i+1]<<8;i+=2
        if not 0<offset<=len(out):raise ValueError('Invalid LZ4 offset')
        n=length(token&15)+4
        if len(out)+n>size:raise ValueError('LZ4 output exceeds expected size')
        # Repeat only the already-produced match period; handle overlapping runs.
        period=out[-offset:]
        out.extend((period*((n+offset-1)//offset))[:n])
    if len(out)!=size:raise ValueError('LZ4 output size mismatch')
    return bytes(out)
