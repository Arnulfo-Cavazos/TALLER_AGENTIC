import os
import tempfile
from threading import Lock

# Simple in-process lock (suficiente para una sola réplica)
file_lock = Lock()

def get_temp_path(filename: str):
    tmp = tempfile.gettempdir()
    return os.path.join(tmp, filename)
