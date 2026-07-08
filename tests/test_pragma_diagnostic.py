import sys
import os
import sqlite3
import random
import threading
import json

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from src.checkpointer import SQLiteCheckpointer

# A checkpointer that does NOT run journal_mode=WAL on every connection
class StableSQLiteCheckpointer(SQLiteCheckpointer):
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        # Do not run journal_mode=WAL here; rely on it being set during init_db or persistent
        return conn

    def init_db(self):
        with self._lock:
            # For init, we explicitly set WAL mode
            conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=NORMAL;")
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS checkpoints (
                        thread_id TEXT PRIMARY KEY,
                        state TEXT,
                        events TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
            finally:
                conn.close()

def run_diagnostic():
    # Test StableSQLiteCheckpointer
    cp = StableSQLiteCheckpointer(db_path=os.path.join(os.path.dirname(__file__), "..", "data", "stable_checkpoints.db"))
    
    # Clean database
    conn = sqlite3.connect(cp.db_path)
    conn.execute("DELETE FROM checkpoints")
    conn.commit()
    conn.close()

    errors = []
    num_threads = 15
    ops_per_thread = 30
    barrier = threading.Barrier(num_threads)

    def worker(thread_idx):
        barrier.wait()
        for i in range(ops_per_thread):
            t_id = f"stable_{thread_idx}_op_{i}"
            try:
                val = {"val": i}
                cp.save(t_id, val)
                
                # Check via checkpointer load
                res = cp.load(t_id)
                
                if res is None:
                    errors.append(f"Thread {thread_idx} op {i}: cp.load returned None for {t_id}")
                elif res[0].get("val") != i:
                    errors.append(f"Thread {thread_idx} op {i}: cp.load returned val={res[0].get('val')} for {t_id}")
            except Exception as e:
                errors.append(f"Thread {thread_idx} op {i} exception: {type(e).__name__}: {e}")

    threads = []
    for i in range(num_threads):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    print("Stable Checkpointer: Total errors across 15 threads / 450 ops:", len(errors))
    
    # Now let's test the original checkpointer with the same load (15 threads, 30 ops)
    cp_orig = SQLiteCheckpointer(db_path=os.path.join(os.path.dirname(__file__), "..", "data", "orig_checkpoints.db"))
    conn_orig = sqlite3.connect(cp_orig.db_path)
    conn_orig.execute("DELETE FROM checkpoints")
    conn_orig.commit()
    conn_orig.close()

    errors_orig = []
    barrier_orig = threading.Barrier(num_threads)

    def worker_orig(thread_idx):
        barrier_orig.wait()
        for i in range(ops_per_thread):
            t_id = f"orig_{thread_idx}_op_{i}"
            try:
                val = {"val": i}
                cp_orig.save(t_id, val)
                
                res = cp_orig.load(t_id)
                if res is None:
                    errors_orig.append(f"Thread {thread_idx} op {i}: cp_orig.load returned None for {t_id}")
            except Exception as e:
                errors_orig.append(f"Thread {thread_idx} op {i} exception: {type(e).__name__}: {e}")

    threads_orig = []
    for i in range(num_threads):
        t = threading.Thread(target=worker_orig, args=(i,))
        threads_orig.append(t)
        t.start()

    for t in threads_orig:
        t.join()

    print("Original Checkpointer: Total errors across 15 threads / 450 ops:", len(errors_orig))

if __name__ == "__main__":
    run_diagnostic()
