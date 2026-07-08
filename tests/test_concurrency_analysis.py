import os
import sys
import sqlite3
import threading
import json
import time

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from src.checkpointer import SQLiteCheckpointer
from tests.utils import reset_inventory

def run_experiment(name, get_connection_fn):
    print(f"\n--- Running Experiment: {name} ---")
    db_path = os.path.abspath(os.path.join(base_dir, "data", f"checkpoints_{name}.db"))
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception:
            pass
            
    # Subclass SQLiteCheckpointer to override _get_connection
    class CustomCheckpointer(SQLiteCheckpointer):
        def __init__(self):
            super().__init__(db_path=db_path)
            
        def _get_connection(self):
            return get_connection_fn(self.db_path)

    cp = CustomCheckpointer()
    
    num_threads = 10
    ops_per_thread = 50
    barrier = threading.Barrier(num_threads)
    errors = []
    
    def worker(thread_idx):
        barrier.wait()
        for i in range(ops_per_thread):
            t_id = f"exp_{thread_idx}_op_{i}"
            state = {"val": i}
            try:
                cp.save(t_id, state)
                
                # Check via cp.load
                res = cp.load(t_id)
                if res is None:
                    # Let's check direct connection to see if it actually exists in db
                    conn_direct = sqlite3.connect(db_path)
                    try:
                        cursor = conn_direct.cursor()
                        cursor.execute("SELECT state FROM checkpoints WHERE thread_id = ?", (t_id,))
                        row_direct = cursor.fetchone()
                    finally:
                        conn_direct.close()
                    errors.append({
                        "thread": thread_idx,
                        "op": i,
                        "error_type": "load_returned_none",
                        "direct_val": row_direct[0] if row_direct else None
                    })
                elif res[0].get("val") != i:
                    errors.append({
                        "thread": thread_idx,
                        "op": i,
                        "error_type": "val_mismatch",
                        "expected": i,
                        "got": res[0].get("val")
                    })
            except Exception as e:
                errors.append({
                    "thread": thread_idx,
                    "op": i,
                    "error_type": "exception",
                    "msg": f"{type(e).__name__}: {str(e)}"
                })

    threads = []
    for i in range(num_threads):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    print(f"Completed '{name}'. Total operations: {num_threads * ops_per_thread}. Total errors: {len(errors)}")
    if errors:
        print("First 5 errors:")
        for err in errors[:5]:
            print("  ", err)
    else:
        print("Success! No errors.")
    return len(errors)

# 1. Baseline: PRAGMAs on every connection (like src/checkpointer.py)
def get_connection_baseline(db_path):
    conn = sqlite3.connect(db_path, timeout=30.0, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

# 2. Optimized: No PRAGMAs on every connection (only when initializing)
def get_connection_no_pragmas(db_path):
    conn = sqlite3.connect(db_path, timeout=30.0, check_same_thread=False)
    return conn

# 3. Explicit Transaction / Isolation Level change
def get_connection_with_isolation(db_path):
    conn = sqlite3.connect(db_path, timeout=30.0, check_same_thread=False, isolation_level=None)
    # in autocommit mode
    return conn

if __name__ == "__main__":
    run_experiment("Baseline (PRAGMAs on every connection)", get_connection_baseline)
    run_experiment("Optimized (No PRAGMAs on connection)", get_connection_no_pragmas)
    run_experiment("Autocommit Mode (isolation_level=None)", get_connection_with_isolation)
