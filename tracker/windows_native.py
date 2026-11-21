"""Read-only Win32 process access and bounded local named-pipe transport.
No debug privilege, remote endpoints, process writes, or injected code.
"""
import ctypes as C
from ctypes import wintypes as W
import os
import re
import time
from pathlib import Path

if os.name == 'nt':
    K=C.WinDLL('kernel32',use_last_error=True)
    A=C.WinDLL('advapi32',use_last_error=True)
    def api(dll,name,args,result=W.BOOL):
        fn=getattr(dll,name);fn.argtypes=args;fn.restype=result;return fn
    api(K,'CloseHandle',[W.HANDLE])
    api(K,'OpenProcess',[W.DWORD,W.BOOL,W.DWORD],W.HANDLE)
    api(K,'GetCurrentProcess',[],W.HANDLE)
    api(K,'QueryFullProcessImageNameW',[W.HANDLE,W.DWORD,W.LPWSTR,C.POINTER(W.DWORD)])
    api(K,'GetProcessTimes',[W.HANDLE,C.POINTER(W.FILETIME),C.POINTER(W.FILETIME),C.POINTER(W.FILETIME),C.POINTER(W.FILETIME)])
    api(K,'ReadProcessMemory',[W.HANDLE,C.c_void_p,C.c_void_p,C.c_size_t,C.POINTER(C.c_size_t)])
    api(K,'VirtualQueryEx',[W.HANDLE,C.c_void_p,C.c_void_p,C.c_size_t],C.c_size_t)
    api(A,'OpenProcessToken',[W.HANDLE,W.DWORD,C.POINTER(W.HANDLE)])
    api(A,'GetTokenInformation',[W.HANDLE,C.c_int,C.c_void_p,W.DWORD,C.POINTER(W.DWORD)])
    api(A,'EqualSid',[C.c_void_p,C.c_void_p])

class MemoryInfo(C.Structure):
    _fields_=[('BaseAddress',C.c_void_p),('AllocationBase',C.c_void_p),('AllocationProtect',W.DWORD),
              ('PartitionId',W.WORD),('RegionSize',C.c_size_t),('State',W.DWORD),('Protect',W.DWORD),('Type',W.DWORD)]

class ProcessEntry(C.Structure):
    _fields_=[('dwSize',W.DWORD),('cntUsage',W.DWORD),('th32ProcessID',W.DWORD),('th32DefaultHeapID',C.c_size_t),
              ('th32ModuleID',W.DWORD),('cntThreads',W.DWORD),('th32ParentProcessID',W.DWORD),
              ('pcPriClassBase',W.LONG),('dwFlags',W.DWORD),('szExeFile',W.WCHAR*260)]

class Overlapped(C.Structure):
    _fields_=[('Internal',C.c_size_t),('InternalHigh',C.c_size_t),('Offset',W.DWORD),('OffsetHigh',W.DWORD),('hEvent',W.HANDLE)]

def checked(ok):
    if not ok: raise C.WinError(C.get_last_error())
    return ok

def token_user(process):
    token=W.HANDLE();checked(A.OpenProcessToken(process,8,C.byref(token)))
    try:
        size=W.DWORD();A.GetTokenInformation(token,1,None,0,C.byref(size))
        if not 0<size.value<=65536:raise OSError('Cannot identify process owner')
        buf=C.create_string_buffer(size.value)
        checked(A.GetTokenInformation(token,1,buf,size,C.byref(size)))
        return buf
    finally:K.CloseHandle(token)

def same_user(process):
    ours=token_user(K.GetCurrentProcess());theirs=token_user(process)
    if not A.EqualSid(C.cast(ours,C.POINTER(C.c_void_p))[0],C.cast(theirs,C.POINTER(C.c_void_p))[0]):
        raise PermissionError('Game process belongs to another Windows account')

def process_identity(pid,expected_exe=None,memory=False):
    handle=checked(K.OpenProcess(0x410 if memory else 0x1000,False,pid))
    try:
        same_user(handle)
        size=W.DWORD(32768);buf=C.create_unicode_buffer(size.value)
        checked(K.QueryFullProcessImageNameW(handle,0,buf,C.byref(size)))
        if expected_exe and os.path.normcase(os.path.realpath(buf.value))!=os.path.normcase(os.path.realpath(expected_exe)):
            raise ValueError('Running executable differs from configured game')
        times=[W.FILETIME() for _ in range(4)]
        checked(K.GetProcessTimes(handle,*[C.byref(t) for t in times]))
        born=(times[0].dwHighDateTime<<32)|times[0].dwLowDateTime
        return handle,(pid,born),buf.value
    except BaseException:K.CloseHandle(handle);raise

def find_process(exe):
    api(K,'CreateToolhelp32Snapshot',[W.DWORD,W.DWORD],W.HANDLE)
    api(K,'Process32FirstW',[W.HANDLE,C.POINTER(ProcessEntry)])
    api(K,'Process32NextW',[W.HANDLE,C.POINTER(ProcessEntry)])
    handle=K.CreateToolhelp32Snapshot(2,0)
    if handle==C.c_void_p(-1).value:raise C.WinError(C.get_last_error())
    matches=[]
    try:
        entry=ProcessEntry();entry.dwSize=C.sizeof(entry)
        more=K.Process32FirstW(handle,C.byref(entry))
        while more:
            if entry.szExeFile.casefold()==Path(exe).name.casefold():
                try:
                    h,identity,_=process_identity(entry.th32ProcessID,exe)
                    K.CloseHandle(h);matches.append(identity[0])
                except (OSError,ValueError):pass
            more=K.Process32NextW(handle,C.byref(entry))
    finally:K.CloseHandle(handle)
    if len(matches)!=1:raise ValueError('Start the configured game (exactly one instance)')
    return matches[0]

class ProcessMemory:
    def __init__(self,pid,expected_exe):
        self.handle,self.identity,self.exe=process_identity(pid,expected_exe,memory=True)
    def close(self):
        if self.handle:K.CloseHandle(self.handle);self.handle=None
    def read(self,address,size):
        if not 0<size<=65536 or not any(lo<=address and address+size<=hi for lo,hi in ((0x7100000000,0x7200000000),(0x7800000000,0x7b00000000))):
            raise ValueError('Memory read outside allowed game regions')
        cursor=address;end=address+size
        while cursor<end:
            info=MemoryInfo()
            checked(K.VirtualQueryEx(self.handle,C.c_void_p(cursor),C.byref(info),C.sizeof(info)))
            if info.State!=0x1000 or info.Protect&0x100 or (info.Protect&0xff) not in (2,4,8,0x20,0x40,0x80):
                raise ValueError('Game data is not readable yet')
            limit=(info.BaseAddress or 0)+info.RegionSize
            if limit<=cursor:raise ValueError('Invalid memory region')
            cursor=min(end,limit)
        buf=C.create_string_buffer(size);actual=C.c_size_t()
        checked(K.ReadProcessMemory(self.handle,C.c_void_p(address),buf,size,C.byref(actual)))
        if actual.value!=size:raise ValueError('Short game memory read')
        return buf.raw

class NamedPipe:
    def __init__(self,name,expected_exe=None,timeout=2):
        if os.name!='nt':raise OSError('Windows named pipes require Windows')
        prefix='\\\\.\\pipe\\'
        name=str(name)
        if name.startswith(prefix):name=name[len(prefix):]
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,160}',name):raise ValueError('Expected a local pipe name')
        self.name=prefix+name;self.timeout=timeout;self.buffer=b'';self.handle=None
        api(K,'CreateFileW',[W.LPCWSTR,W.DWORD,W.DWORD,C.c_void_p,W.DWORD,W.DWORD,W.HANDLE],W.HANDLE)
        api(K,'WaitNamedPipeW',[W.LPCWSTR,W.DWORD])
        api(K,'GetNamedPipeServerProcessId',[W.HANDLE,C.POINTER(W.ULONG)])
        api(K,'CreateEventW',[C.c_void_p,W.BOOL,W.BOOL,W.LPCWSTR],W.HANDLE)
        api(K,'ReadFile',[W.HANDLE,C.c_void_p,W.DWORD,C.POINTER(W.DWORD),C.POINTER(Overlapped)])
        api(K,'WriteFile',[W.HANDLE,C.c_void_p,W.DWORD,C.POINTER(W.DWORD),C.POINTER(Overlapped)])
        api(K,'GetOverlappedResult',[W.HANDLE,C.POINTER(Overlapped),C.POINTER(W.DWORD),W.BOOL])
        api(K,'CancelIoEx',[W.HANDLE,C.POINTER(Overlapped)])
        api(K,'WaitForSingleObject',[W.HANDLE,W.DWORD],W.DWORD)
        deadline=time.monotonic()+timeout
        while True:
            # SECURITY_SQOS_PRESENT|SECURITY_IDENTIFICATION: server cannot impersonate us.
            handle=K.CreateFileW(self.name,0xc0000000,0,None,3,0x40000000|0x100000|0x10000,None)
            if handle!=C.c_void_p(-1).value:break
            error=C.get_last_error()
            if error!=231 or time.monotonic()>=deadline:raise C.WinError(error)
            K.WaitNamedPipeW(self.name,max(1,int((deadline-time.monotonic())*1000)))
        self.handle=handle
        try:
            pid=W.ULONG();checked(K.GetNamedPipeServerProcessId(handle,C.byref(pid)))
            proc,self.identity,_=process_identity(pid.value,expected_exe)
            K.CloseHandle(proc)
        except BaseException:self.close();raise
    def close(self):
        if self.handle:K.CloseHandle(self.handle);self.handle=None
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
    def transfer(self,buf,size,write=False,timeout=None):
        ov=Overlapped();ov.hEvent=checked(K.CreateEventW(None,True,False,None));actual=W.DWORD()
        try:
            fn=K.WriteFile if write else K.ReadFile
            ok=fn(self.handle,buf,size,C.byref(actual),C.byref(ov))
            if not ok:
                error=C.get_last_error()
                if error!=997:raise C.WinError(error)
                if K.WaitForSingleObject(ov.hEvent,max(1,int((self.timeout if timeout is None else timeout)*1000)))!=0:
                    K.CancelIoEx(self.handle,C.byref(ov))
                    K.GetOverlappedResult(self.handle,C.byref(ov),C.byref(actual),True)
                    raise TimeoutError('Longshot pipe response timed out')
                checked(K.GetOverlappedResult(self.handle,C.byref(ov),C.byref(actual),False))
            return actual.value
        finally:K.CloseHandle(ov.hEvent)
    def sendall(self,data):
        if not 0<len(data)<=65536:raise ValueError('Invalid control request size')
        sent=0;deadline=time.monotonic()+self.timeout
        while sent<len(data):
            remaining=deadline-time.monotonic()
            if remaining<=0:raise TimeoutError('Control write timed out')
            buf=C.create_string_buffer(data[sent:]);n=self.transfer(buf,len(data)-sent,True,remaining)
            if not n:raise OSError('Control pipe closed')
            sent+=n
    def readline(self,limit):
        deadline=time.monotonic()+self.timeout
        while b'\n' not in self.buffer and len(self.buffer)<limit:
            remaining=deadline-time.monotonic()
            if remaining<=0:raise TimeoutError('Control read timed out')
            buf=C.create_string_buffer(min(4096,limit-len(self.buffer)))
            n=self.transfer(buf,len(buf),timeout=remaining)
            if not n:raise OSError('Control pipe closed')
            self.buffer+=buf.raw[:n]
        end=self.buffer.find(b'\n')+1
        if not end:end=min(limit,len(self.buffer))
        result,self.buffer=self.buffer[:end],self.buffer[end:]
        return result
