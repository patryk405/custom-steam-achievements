"""Experimental read-only Recompia 2.0.1 memory reader and local socket client.
Layout: Dittobyte/Recompia 4d7c1ff6f0e8cb7f23fb1f139495c55dc2130496,
pkp_layout.h, pkp_coop_discovery.cpp, pkp_coop_unlocks.cpp, nxrt/memory.h.
GPL-3.0-or-later (see licenses/PokoHex-GPL-3.0.txt). No injection/game writes.
"""
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import socket
import struct
import time
from .pokopia import LAYOUT

BASE = 0x7100000000
BUILD = '76a489f3bd3642fa5e18bd83d32c98ba'
PROTOCOL = 'csa-pokopia-memory-v1'


def nso_probes(path):
    """Check supplied main's build and text hash, then bind reads to its code."""
    with Path(path).open('rb') as f: raw=f.read(128*1024*1024+1)
    if not 0x100 <= len(raw) <= 128*1024*1024 or raw[:4]!=b'NSO0' or raw[0x40:0x50].hex()!=BUILD:
        raise ValueError('Expected Pokopia 2.0.1 main NSO, build '+BUILD)
    flags=struct.unpack_from('<I',raw,12)[0]
    offset,address,size=struct.unpack_from('<III',raw,0x10)
    compressed=struct.unpack_from('<I',raw,0x60)[0]
    if address!=0 or not 0x2e40c4 <= size <= 64*1024*1024 or offset<0x100 or not 0<compressed<=len(raw)-offset:
        raise ValueError('Invalid main text segment')
    text=raw[offset:offset+compressed]
    if flags&1:
        from lz4_block import decompress
        text=decompress(text,size)
    if len(text)!=size or hashlib.sha256(text).digest()!=raw[0xa0:0xc0]:
        raise ValueError('Main text checksum mismatch')
    if struct.unpack_from('<I',text,0xb1030)[0]!=0xf2c0002d:
        raise ValueError('Main code signature differs')
    # Fixed code windows, compared with the actual mapped game, not its filename.
    return [(BASE+offset,text[offset:offset+64]) for offset in (0xb1030,0x2e7240,0x2e4084) if offset+64<=size]


class ProcessMemory:
    def __init__(self,pid):
        self.pid=pid
        # Read-only descriptor. Wrapper is the game's parent: no ptrace attach,
        # PR_SET_PTRACER, elevated permissions or sysctl changes are needed.
        self.fd=os.open(f'/proc/{pid}/mem',os.O_RDONLY|os.O_CLOEXEC)
        self.refresh()
    def close(self): os.close(self.fd)
    def refresh(self):
        self.ranges=[]
        for line in Path(f'/proc/{self.pid}/maps').read_text().splitlines():
            interval,perms,*_=line.split()
            if perms.startswith('r'):
                lo,hi=(int(s,16) for s in interval.split('-'));self.ranges.append((lo,hi))
    def read(self,address,size):
        if not 0<size<=65536 or not (BASE<=address<0x7200000000 or 0x7800000000<=address<0x7b00000000):
            raise ValueError('Memory read outside allowed game regions')
        end=address+size;cursor=address
        for lo,hi in self.ranges:
            if lo<=cursor<hi: cursor=min(hi,end)
            if cursor==end:break
        if cursor!=end:raise ValueError('Game data is not mapped yet')
        data=os.pread(self.fd,size,address)
        if len(data)!=size:raise ValueError('Short game memory read')
        return data


class Sampler:
    def __init__(self):self.previous=None
    def sample(self,read,probes,now=None):
        now=time.monotonic() if now is None else now
        def unpack(fmt,address):return struct.unpack(fmt,read(address,struct.calcsize(fmt)))[0]
        def ptr(address):
            p=unpack('<Q',address)
            if p%8 or not 0x7800000000<=p<0x7b00000000:raise ValueError('Waiting for game objects')
            return p
        completed=False
        try:
            for address,expected in probes:
                if read(address,len(expected))!=expected:raise ValueError('Running game does not match supported main')
            root=ptr(BASE+0x3561930);state=ptr(BASE+0x3561710);manager=ptr(BASE+0x3561928);player=ptr(manager+0x30)
            if unpack('<Q',player)!=BASE+0x322fda8:raise ValueError('Unexpected player class')
            stage=unpack('<B',state+0x18)
            if not 1<=stage<=17 or unpack('<B',player+0xa9ec)&0x20:raise ValueError('Waiting for controllable gameplay')
            clock=unpack('<d',root+0x4a5418)
            if not math.isfinite(clock) or not 0<=clock<1e9:raise ValueError('Invalid play clock')
            identity=(root,state,player,stage)
            def snapshot():
                dex=read(root+0x6fa1a4,1024);hab=read(root+0x6f89a4,512*12)
                recipes=read(root+0x6cfdec,1500*6);moves=read(root+0x6d82f0,64*8);flags=read(root+0x4a26a8,32)
                return {'dex':sum((dex[i]&3)==3 for i in LAYOUT['dex']),
                        'habitats':sum(bool(hab[i*12]&2) for i in LAYOUT['habitats']),
                        'recipes':sum(bool(recipes[i*6+4]&2) for i in LAYOUT['recipes']),
                        'moves':sum(bool(moves[i*8+4]&1) and (i!=10 or bool(flags[7]&1)) and (i!=11 or bool(flags[7]&2)) for i in (1,2,3,4,5,6,10,11,12,13)),
                        'water_gun_uses':struct.unpack_from('<I',moves,3*8)[0]}
            values=snapshot()
            if values!=snapshot() or (root,state,player,stage)!=(ptr(BASE+0x3561930),ptr(BASE+0x3561710),ptr(ptr(BASE+0x3561928)+0x30),unpack('<B',state+0x18)):
                raise ValueError('Game state changed during sampling')
            previous=self.previous;self.previous=(identity,clock,now);completed=True
            # This is the save's accumulated play time, not a frame clock. It can
            # stay unchanged during active gameplay; freshness comes from the
            # live process reads and monotonic sampling time. Keep it only as
            # a discontinuity check when a save is loaded or replaced.
            if not previous or previous[0]!=identity or not 0<now-previous[2]<=6:
                raise ValueError('Waiting for two stable gameplay samples')
            if not 0<=clock-previous[1]<=max(30,4*(now-previous[2])):
                raise ValueError(f'Waiting after a play-time discontinuity (delta={clock-previous[1]:.3f}, elapsed={now-previous[2]:.3f}, dex={values["dex"]})')
            return values
        except (OSError,ValueError,struct.error):
            # Retain only the clock baseline created by a complete snapshot.
            if not completed:self.previous=None
            raise


class LiveReader:
    def read_metrics(self,path):
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as sock:
            sock.settimeout(1.5);sock.connect(str(path))
            _,uid,_=struct.unpack('3i',sock.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
            if uid!=os.getuid():raise ValueError('Live reader belongs to another user')
            sock.sendall(b'status\n')
            with sock.makefile('rb') as stream:raw=stream.readline(8193)
        if len(raw)>8192 or not raw.endswith(b'\n'):raise ValueError('Invalid live response')
        event=json.loads(raw)
        if event.get('protocol')!=PROTOCOL or event.get('build')!=BUILD or event.get('ready') is not True:
            raise ValueError(event.get('message','Waiting for Pokopia live reader'))
        stamp=event.get('at')
        if type(stamp) not in (int,float) or not math.isfinite(stamp) or not 0<=time.monotonic()-stamp<=3:
            raise ValueError('Stale Pokopia live sample')
        metrics=event.get('metrics');limits={'dex':len(LAYOUT['dex']),'habitats':len(LAYOUT['habitats']),'recipes':len(LAYOUT['recipes']),'moves':10,'water_gun_uses':0xffffffff}
        if not isinstance(metrics,dict) or set(metrics)!=set(limits) or any(type(metrics[k]) is not int or not 0<=metrics[k]<=n for k,n in limits.items()):
            raise ValueError('Invalid live metrics')
        return metrics
