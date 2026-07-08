import os
import sys
import unittest
import threading
import time
import json
import sqlite3
from concurrent.futures import ProcessPoolExecutor, as_completed

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from src.checkpointer import SQLiteCheckpointer
from src.graph import read_inventory, write_inventory
from tests.utils import reset_inventory, INVENTORY_PATH

DB_STRESS_PATH = os.path.abspath(
    os.path.join(base_dir, "data", "checkpoints_stress_challenger.db")
)

def run_sqlite_process_worker(process_idx, ops_count, db_path):
    errors = []
    from src.checkpointer import SQLiteCheckpointer
    cp = SQLiteCheckpointer(db_path=db_path)
    for op_idx in range(ops_count):
        thread_id = f"proc_{process_idx}_op_{op_idx}"
        state = {"value": op_idx, "nested": {"data": [process_idx]}}
        try:
            # Write
            cp.save(thread_id, state, events=[{"event": "test"}])
            # Read
            loaded = cp.load(thread_id)
            if loaded is None:
                errors.append(f"Process {process_idx} op {op_idx}: loaded state is None")
            else:
                loaded_state, loaded_events = loaded
                if loaded_state.get("value") != op_idx:
                    errors.append(f"Process {process_idx} op {op_idx}: state mismatch: expected {op_idx}, got {loaded_state.get('value')}")
        except Exception as e:
            errors.append(f"Process {process_idx} op {op_idx} failed: {type(e).__name__}: {str(e)}")
    return errors

def run_inventory_process_worker(process_idx, ops_count):
    errors = []
    from src.graph import read_inventory, write_inventory
    for op_idx in range(ops_count):
        try:
            # Read
            inv = read_inventory()
            expected_keys = ["Pantalla_HP", "RAM_8GB", "RAM_16GB", "Fuente_Poder", "SSD_1TB", "Mouse_Inalambrico", "Teclado_Bluetooth", "Pasta_Termica", "Ventilador_CPU"]
            for k in expected_keys:
                if k not in inv:
                    errors.append(f"Process {process_idx} op {op_idx}: missing key {k} in inventory")
            
            # Increment a custom key
            proc_key = f"proc_{process_idx}_counter"
            current_val = inv.get(proc_key, 0)
            inv[proc_key] = current_val + 1
            
            # Write back
            write_inventory(inv)
            
            # Sleep tiny bit to simulate realistic delay
            time.sleep(0.001)
        except Exception as e:
            errors.append(f"Process {process_idx} op {op_idx} failed: {type(e).__name__}: {str(e)}")
    return errors

class TestStressConcurrency(unittest.TestCase):

    def setUp(self):
        reset_inventory()
        self.checkpointer = SQLiteCheckpointer(db_path=DB_STRESS_PATH)
        # Clean up database
        conn = sqlite3.connect(self.checkpointer.db_path)
        try:
            conn.execute("DELETE FROM checkpoints")
            conn.commit()
        finally:
            conn.close()

    def tearDown(self):
        # Clean up database file after test to keep workspace clean
        if os.path.exists(DB_STRESS_PATH):
            try:
                os.remove(DB_STRESS_PATH)
            except Exception:
                pass
            try:
                os.remove(DB_STRESS_PATH + "-wal")
            except Exception:
                pass
            try:
                os.remove(DB_STRESS_PATH + "-shm")
            except Exception:
                pass

    def test_sqlite_checkpointer_threads_concurrency(self):
        """
        Test that SQLiteCheckpointer handles at least 5 (we do 10) concurrent threads
        performing reads and writes without throwing "database is locked".
        """
        num_threads = 10
        ops_per_thread = 50
        errors = []

        def run_thread(thread_idx):
            cp = SQLiteCheckpointer(db_path=DB_STRESS_PATH)
            for op_idx in range(ops_per_thread):
                thread_id = f"thread_{thread_idx}_op_{op_idx}"
                state = {"value": op_idx, "nested": {"data": [thread_idx]}}
                try:
                    # Write
                    cp.save(thread_id, state, events=[{"event": "test"}])
                    # Read
                    loaded = cp.load(thread_id)
                    if loaded is None:
                        errors.append(f"Thread {thread_idx} op {op_idx}: loaded state is None")
                    else:
                        loaded_state, loaded_events = loaded
                        if loaded_state.get("value") != op_idx:
                            errors.append(f"Thread {thread_idx} op {op_idx}: state mismatch: expected {op_idx}, got {loaded_state.get('value')}")
                except Exception as e:
                    errors.append(f"Thread {thread_idx} op {op_idx} failed: {type(e).__name__}: {str(e)}")

        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=run_thread, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"SQLiteCheckpointer thread concurrency errors: {errors}")

    def test_sqlite_checkpointer_processes_concurrency(self):
        """
        Test that SQLiteCheckpointer handles at least 5 (we do 10) concurrent processes
        performing reads and writes without throwing "database is locked".
        """
        num_processes = 10
        ops_per_process = 50

        with ProcessPoolExecutor(max_workers=num_processes) as executor:
            futures = [
                executor.submit(run_sqlite_process_worker, i, ops_per_process, DB_STRESS_PATH)
                for i in range(num_processes)
            ]
            
            errors = []
            for f in as_completed(futures):
                res = f.result()
                if res:
                    errors.extend(res)

        self.assertEqual(len(errors), 0, f"SQLiteCheckpointer process concurrency errors: {errors}")

    def test_json_inventory_locking_processes_concurrency(self):
        """
        Test that JSON inventory file locking handles at least 5 (we do 10) concurrent processes
        reading/writing to the same inventory.json file using fcntl.flock.
        """
        num_processes = 10
        ops_per_process = 30

        reset_inventory()

        with ProcessPoolExecutor(max_workers=num_processes) as executor:
            futures = [
                executor.submit(run_inventory_process_worker, i, ops_per_process)
                for i in range(num_processes)
            ]
            
            errors = []
            for f in as_completed(futures):
                res = f.result()
                if res:
                    errors.extend(res)

        self.assertEqual(len(errors), 0, f"JSON Inventory locking process concurrency errors: {errors}")
