"""Atomic local JSON persistence with bounded Windows sharing-conflict recovery."""
import json
import os
import tempfile
import time
from pathlib import Path


def process_alive(pid):
    if type(pid)!=int or pid<=0:return False
    if os.name=='nt':
        import ctypes
        from ctypes import wintypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
        kernel.OpenProcess.restype=wintypes.HANDLE
        kernel.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)]
        kernel.CloseHandle.argtypes=[wintypes.HANDLE]
        handle=kernel.OpenProcess(0x1000,False,pid)
        if not handle:return False
        try:
            code=wintypes.DWORD()
            return bool(kernel.GetExitCodeProcess(handle,ctypes.byref(code))) and code.value==259
        finally:kernel.CloseHandle(handle)
    try:
        os.kill(pid,0)
        return True
    except ProcessLookupError:return False
    except PermissionError:return True


def write_json(path, value):
    path=Path(path)
    fd,name=tempfile.mkstemp(prefix='.write-',suffix='.json',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as stream:
            json.dump(value,stream,ensure_ascii=False,indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        for attempt in range(7):
            try:
                os.replace(name,path)
                break
            except PermissionError:
                if attempt==6:raise
                time.sleep(.01*(2**attempt))
    finally:
        if os.path.exists(name):os.unlink(name)
