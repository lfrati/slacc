import sys
import torch


def gpu_info():
    for device in range(torch.cuda.device_count()):
        print(f"id:{device} - name:{torch.cuda.get_device_name(device)}")
    print()
    curr_device = torch.cuda.current_device()
    print(f"Current device: {curr_device} Has cuda? {torch.cuda.is_available()}")


print("Training neural networks, lowering losses, learning AI!")
print("These are my flags: ", sys.argv[1:])
gpu_info()
