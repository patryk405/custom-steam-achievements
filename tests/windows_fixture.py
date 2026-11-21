"""Disposable test child, never a game. Used only by Windows CI integration tests."""
import ctypes as C
from ctypes import wintypes as W
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tracker'))
from windows_native import K, api, checked

if sys.argv[1]=='memory':
    from test_pokopia_live import MemoryFixture
    fixture=MemoryFixture()
    api(K,'VirtualAlloc',[C.c_void_p,C.c_size_t,W.DWORD,W.DWORD],C.c_void_p)
    for base,size in ((0x7100000000,0x3600000),(0x7801000000,0x6000000)):
        if K.VirtualAlloc(C.c_void_p(base),size,0x2000,4)!=base:raise OSError('Fixture address unavailable')
    for address,data in fixture.blocks.items():
        start=address&~4095;end=(address+len(data)+4095)&~4095
        checked(K.VirtualAlloc(C.c_void_p(start),end-start,0x1000,4))
        C.memmove(address,bytes(data),len(data))
    print(json.dumps({'ready':True,'probes':[(a,b.hex()) for a,b in fixture.probes]}),flush=True)
    for line in sys.stdin:
        if line.strip()=='dex':
            from adapters.pokopia import LAYOUT
            C.c_ubyte.from_address(fixture.root+0x6fa1a4+LAYOUT['dex'][0]).value=3
        print('ok',flush=True)
else:
    api(K,'CreateNamedPipeW',[W.LPCWSTR,W.DWORD,W.DWORD,W.DWORD,W.DWORD,W.DWORD,W.DWORD,C.c_void_p],W.HANDLE)
    api(K,'ConnectNamedPipe',[W.HANDLE,C.c_void_p])
    api(K,'ReadFile',[W.HANDLE,C.c_void_p,W.DWORD,C.POINTER(W.DWORD),C.c_void_p])
    api(K,'WriteFile',[W.HANDLE,C.c_void_p,W.DWORD,C.POINTER(W.DWORD),C.c_void_p])
    api(K,'FlushFileBuffers',[W.HANDLE])
    api(K,'DisconnectNamedPipe',[W.HANDLE])
    name=sys.argv[2];scenario=sys.argv[3];frame=100;first=True
    while True:
        handle=K.CreateNamedPipeW('\\\\.\\pipe\\'+name,3,8,255,65536,65536,0,None)
        if handle==C.c_void_p(-1).value:raise C.WinError(C.get_last_error())
        if first:print('ready',flush=True);first=False
        ok=K.ConnectNamedPipe(handle,None)
        if not ok and C.get_last_error()!=535:raise C.WinError(C.get_last_error())
        try:
            raw=b''
            while True:
                b=C.create_string_buffer(1);n=W.DWORD()
                if not K.ReadFile(handle,b,1,C.byref(n),None) or not n.value:break
                raw+=b.raw
                if not raw.endswith(b'\n'):continue
                command=json.loads(raw);raw=b''
                if scenario=='timeout':
                    import time;time.sleep(5);break
                if command['cmd']=='status':
                    from test_longshot import sample
                    reply=sample(frame=frame,x=(frame-100)/10,rupees=1)
                    reply['game']['t']=1000+frame/30
                    if scenario=='version':reply['version']='unverified'
                    payload=json.dumps(reply)+'\n';frame+=60
                else:
                    payload=json.dumps({'id':2,'ok':True})+'\n'+json.dumps({'event':'oot','sub':2,'frame':frame,'game':{'frame':frame,'loading':False,'flags':{key:1 for key in command['flags']}}})+'\n'
                data=payload.encode();buf=C.create_string_buffer(data);n=W.DWORD()
                if not K.WriteFile(handle,buf,len(data),C.byref(n),None):break
                K.FlushFileBuffers(handle)
        finally:K.DisconnectNamedPipe(handle);K.CloseHandle(handle)
