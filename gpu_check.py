import sys
import torch
import psutil


def get_size(bytes, suffix="B"):
    """
    Scale bytes to its proper format
    e.g:
        1253656 => '1.20MB'
        1253656678 => '1.17GB'
    """
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor:
            return f"{bytes:.2f}{unit}{suffix}"
        bytes /= factor


def show_gpu_info():
    for device in range(torch.cuda.device_count()):
        print(f"id:{device} - name:{torch.cuda.get_device_name(device)}")
    curr_device = torch.cuda.current_device()
    has_cuda = torch.cuda.is_available()
    print(f"Current device: {curr_device} Has cuda? {has_cuda}")


print("Flags: ", sys.argv[1:])
try:
    a = torch.ones(10)
    a.normal_(0, 1)
except:
    print("ERROR: TORCH test failed!")
else:
    print("OK: TORCH test passed!")

try:
    b = torch.ones(10).cuda()
    b.normal_(0, 1)
except:
    print("ERROR: CUDA test failed!")
else:
    print("OK: CUDA test passed!")

print("=" * 20, "INFO", "=" * 20)
# number of cores
p = psutil.Process()
try:
    print("Cores:", len(p.cpu_affinity()))
except:
    pass
# memory report seems wrong.
# print("Memory:", {key:get_size(val) for key,val in p.memory_info()._asdict().items()})
print("Torch version:", torch.__version__)
show_gpu_info()
