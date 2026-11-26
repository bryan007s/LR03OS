import ctypes, ctypes.wintypes as wintypes, sys

class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
        ("PrivateUsage", ctypes.c_size_t),
    ]

class IO_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_uint64), ("WriteOperationCount", ctypes.c_uint64),
        ("OtherOperationCount", ctypes.c_uint64), ("ReadTransferCount", ctypes.c_uint64),
        ("WriteTransferCount", ctypes.c_uint64), ("OtherTransferCount", ctypes.c_uint64),
    ]

psapi, kernel32 = ctypes.WinDLL("psapi"), ctypes.WinDLL("kernel32")
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX), wintypes.DWORD]
kernel32.GetProcessIoCounters.argtypes = [wintypes.HANDLE, ctypes.POINTER(IO_COUNTERS)]

pid = int(sys.argv[1])
h = kernel32.OpenProcess(0x0410, False, pid)
pmc = PROCESS_MEMORY_COUNTERS_EX(); pmc.cb = ctypes.sizeof(pmc)
ioc = IO_COUNTERS()
psapi.GetProcessMemoryInfo(h, ctypes.byref(pmc), pmc.cb)
kernel32.GetProcessIoCounters(h, ctypes.byref(ioc))
kernel32.CloseHandle(h)

print({
    "rss_kb": pmc.WorkingSetSize // 1024,
    "vsz_kb": pmc.PagefileUsage // 1024,
    "private_kb": pmc.PrivateUsage // 1024,
    "page_faults": pmc.PageFaultCount,
    "read_bytes": ioc.ReadTransferCount,
    "write_bytes": ioc.WriteTransferCount,
})
