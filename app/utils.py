import os
import tempfile
from threading import Lock

file_lock = Lock()

def get_temp_path(filename: str):
    tmp = tempfile.gettempdir()
    return os.path.join(tmp, filename)
