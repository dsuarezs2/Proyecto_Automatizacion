import os
import json

# Define the baseline stock levels
BASELINE_INVENTORY = {
  "Pantalla_HP": {
    "price": 120.0,
    "stock": 3
  },
  "RAM_8GB": {
    "price": 45.0,
    "stock": 0
  },
  "RAM_16GB": {
    "price": 80.0,
    "stock": 5
  },
  "Fuente_Poder": {
    "price": 90.0,
    "stock": 2
  },
  "SSD_1TB": {
    "price": 110.0,
    "stock": 5
  },
  "Mouse_Inalambrico": {
    "price": 25.0,
    "stock": 10
  },
  "Teclado_Bluetooth": {
    "price": 45.0,
    "stock": 5
  },
  "Pasta_Termica": {
    "price": 15.0,
    "stock": 20
  },
  "Ventilador_CPU": {
    "price": 20.0,
    "stock": 15
  }
}

from src.config import INVENTORY_PATH


def reset_inventory():
    """
    Restores data/inventario.json to its baseline stock levels using file locking.
    """
    # Create the directory if it doesn't exist
    os.makedirs(os.path.dirname(INVENTORY_PATH), exist_ok=True)
    
    # Try importing fcntl for Linux file locking
    try:
        import fcntl
        if not os.path.exists(INVENTORY_PATH):
            with open(INVENTORY_PATH, "w", encoding="utf-8") as f:
                json.dump({}, f)
        with open(INVENTORY_PATH, "r+", encoding="utf-8") as f:
            # Acquire an exclusive lock on the file descriptor
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.seek(0)
                json.dump(BASELINE_INVENTORY, f, indent=2)
                f.truncate()
                f.flush()
                os.fsync(f.fileno())
            finally:
                # Release the lock
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except (ImportError, AttributeError):
        # Fallback for systems without fcntl (e.g. Windows) using a lock file
        lock_path = INVENTORY_PATH + ".lock"
        import time
        start_time = time.time()
        while True:
            try:
                # Try to exclusively create the lock file
                fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                break
            except FileExistsError:
                if time.time() - start_time > 5.0:
                    raise TimeoutError("Could not acquire lock on inventory file")
                time.sleep(0.05)
        
        try:
            with open(INVENTORY_PATH, "w") as f:
                json.dump(BASELINE_INVENTORY, f, indent=2)
        finally:
            try:
                os.close(fd)
            except Exception:
                pass
            try:
                os.remove(lock_path)
            except Exception:
                pass
