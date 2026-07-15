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
  },
  "Pila_CR2032": {
    "price": 5.0,
    "stock": 100
  },
  "Servicio_Mantenimiento_Contactos": {
    "price": 15.0,
    "stock": 999
  },
  "Servicio_Recuperacion_Sistema": {
    "price": 30.0,
    "stock": 999
  },
  "Servicio_Aislamiento_Placa": {
    "price": 25.0,
    "stock": 999
  },
  "Servicio_Optimizacion_Drivers": {
    "price": 20.0,
    "stock": 999
  },
  "Servicio_Limpieza_Software": {
    "price": 15.0,
    "stock": 999
  },
  "Servicio_Configuracion_Red": {
    "price": 20.0,
    "stock": 999
  },
  "Tarjeta_WiFi_PCIe": {
    "price": 35.0,
    "stock": 10
  },
  "Tarjeta_Grafica_GPU": {
    "price": 250.0,
    "stock": 5
  },
  "Cable_HDMI_2.0": {
    "price": 15.0,
    "stock": 30
  },
  "Servicio_Reparacion_Jack": {
    "price": 25.0,
    "stock": 999
  },
  "Servicio_Optimizacion_Audio": {
    "price": 15.0,
    "stock": 999
  },
  "Hub_USB_Externo": {
    "price": 15.0,
    "stock": 25
  },
  "Servicio_Recuperacion_Datos": {
    "price": 50.0,
    "stock": 999
  },
  "Servicio_Configuracion_Teclado": {
    "price": 10.0,
    "stock": 999
  },
  "Servicio_Soporte_Impresora": {
    "price": 20.0,
    "stock": 999
  },
  "Servicio_Diagnostico_Software": {
    "price": 25.0,
    "stock": 999
  },
  "Servicio_Instalacion_Librerias": {
    "price": 15.0,
    "stock": 999
  },
  "Servicio_Limpieza_Malware": {
    "price": 30.0,
    "stock": 999
  },
  "Servicio_Limpieza_Disco": {
    "price": 20.0,
    "stock": 999
  },
  "Pendrive_USB_3.0": {
    "price": 20.0,
    "stock": 40
  },
  "Licencia_Windows_11_64bit": {
    "price": 45.0,
    "stock": 100
  },
  "GPU_Nvidia_RTX_4060": {
    "price": 320.0,
    "stock": 5
  },
  "GPU_Nvidia_RTX_4070": {
    "price": 600.0,
    "stock": 3
  },
  "GPU_AMD_RX_7600": {
    "price": 270.0,
    "stock": 4
  },
  "CPU_Intel_i5_13400": {
    "price": 210.0,
    "stock": 8
  },
  "CPU_Intel_i7_13700": {
    "price": 380.0,
    "stock": 4
  },
  "CPU_AMD_Ryzen_5_7600X": {
    "price": 230.0,
    "stock": 6
  },
  "CPU_AMD_Ryzen_7_7800X3D": {
    "price": 400.0,
    "stock": 3
  },
  "Placa_ASUS_B650_AM5": {
    "price": 180.0,
    "stock": 5
  },
  "Placa_MSI_B760_LGA1700": {
    "price": 150.0,
    "stock": 6
  },
  "RAM_DDR4_8GB": {
    "price": 25.0,
    "stock": 20
  },
  "RAM_DDR4_16GB": {
    "price": 45.0,
    "stock": 15
  },
  "RAM_DDR5_16GB": {
    "price": 60.0,
    "stock": 12
  },
  "RAM_DDR5_32GB": {
    "price": 110.0,
    "stock": 8
  },
  "SSD_NVMe_500GB": {
    "price": 45.0,
    "stock": 15
  },
  "SSD_NVMe_1TB": {
    "price": 85.0,
    "stock": 10
  },
  "SSD_NVMe_2TB": {
    "price": 150.0,
    "stock": 6
  },
  "HDD_WesternDigital_1TB": {
    "price": 45.0,
    "stock": 10
  },
  "HDD_WesternDigital_2TB": {
    "price": 65.0,
    "stock": 8
  },
  "Fuente_Corsair_750W_Gold": {
    "price": 120.0,
    "stock": 6
  },
  "Fuente_EVGA_600W_Bronze": {
    "price": 65.0,
    "stock": 10
  },
  "Gabinete_NZXT_H5_Flow": {
    "price": 95.0,
    "stock": 5
  },
  "Gabinete_Corsair_4000D": {
    "price": 100.0,
    "stock": 4
  },
  "Disipador_Noctua_NH_D15": {
    "price": 110.0,
    "stock": 4
  },
  "Refrigeracion_Liquida_240mm": {
    "price": 90.0,
    "stock": 5
  },
  "Monitor_LG_24_FHD": {
    "price": 130.0,
    "stock": 8
  },
  "Monitor_ASUS_27_2K_144Hz": {
    "price": 280.0,
    "stock": 4
  },
  "Mouse_Logitech_G502": {
    "price": 65.0,
    "stock": 12
  },
  "Teclado_Mecanico_Redragon": {
    "price": 55.0,
    "stock": 10
  },
  "Auriculares_HyperX_Cloud_II": {
    "price": 90.0,
    "stock": 8
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
            except (FileExistsError, PermissionError):
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
