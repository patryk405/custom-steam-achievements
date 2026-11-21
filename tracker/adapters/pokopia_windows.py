"""Read live Recompia guest memory from one configured native Windows process."""
from pathlib import Path
from .pokopia_live import Sampler, nso_probes

class LiveReader:
    def __init__(self):
        self.configuration=None;self.probes=None;self.identity=None;self.sampler=Sampler()
    def read_metrics(self, manifest):
        from windows_native import ProcessMemory, find_process
        exe=manifest.get('windowsExe');main=manifest.get('windowsMain')
        if not exe or not main:raise ValueError('Configure Pokopia Live: choose pkp.exe and exefs/main in Setup')
        file=Path(main);stat=file.stat()
        config=(exe,str(file),stat.st_mtime_ns,stat.st_size)
        if config!=self.configuration:
            self.probes=nso_probes(file);self.configuration=config
            self.identity=None;self.sampler=Sampler()
        try:
            pid=find_process(exe)
            memory=ProcessMemory(pid,exe)
        except (OSError,ValueError):
            self.identity=None;self.sampler=Sampler();raise
        try:
            if memory.identity!=self.identity:
                self.identity=memory.identity;self.sampler=Sampler()
            return self.sampler.sample(memory.read,self.probes)
        finally:memory.close()
