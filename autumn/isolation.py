"""Resource isolation for a trusted single-user runtime, not an OS security sandbox."""
import os
_JOB=None
def apply_limits():
    global _JOB
    if os.name=='nt':
        import ctypes as c
        from ctypes import wintypes as w
        class BASIC(c.Structure):
            _fields_=[('process_time',c.c_int64),('job_time',c.c_int64),('flags',w.DWORD),('minimum_working_set',c.c_size_t),('maximum_working_set',c.c_size_t),('active_processes',w.DWORD),('affinity',c.c_size_t),('priority',w.DWORD),('scheduling',w.DWORD)]
        class IO(c.Structure): _fields_=[(x,c.c_uint64) for x in ['read_ops','write_ops','other_ops','read_bytes','write_bytes','other_bytes']]
        class EXTENDED(c.Structure): _fields_=[('basic',BASIC),('io',IO),('process_memory',c.c_size_t),('job_memory',c.c_size_t),('peak_process_memory',c.c_size_t),('peak_job_memory',c.c_size_t)]
        kernel=c.WinDLL('kernel32',use_last_error=True)
        kernel.CreateJobObjectW.argtypes=[c.c_void_p,w.LPCWSTR]; kernel.CreateJobObjectW.restype=w.HANDLE
        kernel.SetInformationJobObject.argtypes=[w.HANDLE,c.c_int,c.c_void_p,w.DWORD]; kernel.SetInformationJobObject.restype=w.BOOL
        kernel.GetCurrentProcess.restype=w.HANDLE
        kernel.AssignProcessToJobObject.argtypes=[w.HANDLE,w.HANDLE]; kernel.AssignProcessToJobObject.restype=w.BOOL
        kernel.IsProcessInJob.argtypes=[w.HANDLE,w.HANDLE,c.POINTER(w.BOOL)]
        _JOB=kernel.CreateJobObjectW(None,None)
        limits=EXTENDED(); limits.basic.flags=0x2000|0x100|0x8|0x2
        limits.basic.active_processes=1; limits.basic.process_time=60*10_000_000; limits.process_memory=2*1024**3
        if not _JOB or not kernel.SetInformationJobObject(_JOB,9,c.byref(limits),c.sizeof(limits)) or not kernel.AssignProcessToJobObject(_JOB,kernel.GetCurrentProcess()):
            raise c.WinError(c.get_last_error())
        yes=w.BOOL(); kernel.IsProcessInJob(kernel.GetCurrentProcess(),_JOB,c.byref(yes))
        if not yes.value: raise RuntimeError('job_assignment_not_verified')
        return {'kind':'Windows Job Object','assigned':True,'memory_bytes':limits.process_memory,'active_processes':1,'cpu_seconds':60}
    import resource
    resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3)); resource.setrlimit(resource.RLIMIT_CPU,(60,60)); resource.setrlimit(resource.RLIMIT_NOFILE,(128,128))
    return {'kind':'POSIX resource limits','memory_bytes':2*1024**3,'cpu_seconds':60}
