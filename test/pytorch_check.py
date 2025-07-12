# sanity_check_2.py
import torch, torchvision, platform
print("Python :", platform.python_version())
print("Torch   :", torch.__version__)
print("TVision :", torchvision.__version__)
print("CUDA OK :", torch.cuda.is_available())
print("nms op  :", torch.ops.torchvision.nms)     # should print a C++ function handle
