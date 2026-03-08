"""
Windows + Ray + CUDA compatibility fixes.
Must be imported FIRST in any script that uses Flower simulation.
"""

import asyncio
import sys

# Fix asyncio event loop policy for Ray on Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Fix CUDA multiprocessing on Windows (must be called before any CUDA usage)
import torch.multiprocessing as mp
try:
    mp.set_start_method("spawn")
except RuntimeError:
    pass  # already set — safe to ignore
