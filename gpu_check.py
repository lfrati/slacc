import traceback
import sys
import torch
import psutil


def print_header(title):
    width = (80 - len(title) - 2) // 2
    print("=" * width, title, "=" * width)


def get_size(sz_bytes, suffix="B"):
    """
    Scale bytes to its proper format
    e.g:
        1253656 => '1.20MB'
        1253656678 => '1.17GB'
    """
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if sz_bytes < factor:
            return f"{sz_bytes:.2f}{unit}{suffix}"
        sz_bytes /= factor


def print_device_info(device):
    """
    Prints information about the properties and state of the given device.

    :param device: [torch.device or int] device for which to print information.
    """
    print(f"id: {device} - name: {torch.cuda.get_device_name(device)}")
    print(f"    properties: {torch.cuda.get_device_properties(device)}")
    # Extra debug info, if desired.
    #print(f"    processes: {torch.cuda.list_gpu_processes(device)}")
    #print(f"    memory summary:\n{torch.cuda.memory_summary(device)}")


def show_gpu_info():
    has_cuda = torch.cuda.is_available()
    if has_cuda:
        curr_device = torch.cuda.current_device()
    else:
        curr_device = "N/A"
    print(f"Has cuda? {has_cuda}; Current device: {curr_device}")

    print_header("GPU Devices")
    if torch.cuda.device_count() > 0:
        for device in range(torch.cuda.device_count()):
            print_device_info(device)
    else:
        print("(No devices)")


if __name__ == "__main__":

    print("Flags: ", sys.argv[1:])

    try:
        a = torch.ones(10)
        a.normal_(0, 1)
    except Exception:
        print(f"ERROR: TORCH test failed:")
        traceback.print_exc(file=sys.stdout)
    else:
        print("OK: TORCH test passed!")

    try:
        b = torch.ones(10, device='cuda')
        b.normal_(0, 1)
    except Exception:
        print(f"ERROR: CUDA test failed:")
        traceback.print_exc(file=sys.stdout)
    else:
        print("OK: CUDA test passed!")

    print_header("INFO")
    # number of cores
    p = psutil.Process()
    try:
        print("Cores:", len(p.cpu_affinity()))
    except Exception:
        pass

    # memory report seems wrong.
    # print("Memory:", {key:get_size(val) for key,val in p.memory_info()._asdict().items()})

    print("Torch version:", torch.__version__)
    print("CUDA version:", torch.version.cuda)
    # Extra debug info, if desired.
    #print("CUDA compiled for:", torch.cuda.get_arch_list())

    show_gpu_info()
