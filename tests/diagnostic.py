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

def run_diagnostic():
    cp = SQLiteCheckpointer()
    print("Database path:", cp.db_path)
    
    # Clean database
    conn = sqlite3.connect(cp.db_path)
    conn.execute("DELETE FROM checkpoints")
    conn.commit()
    conn.close()

    errors = []
    num_threads = 10
    ops_per_thread = 20
    barrier = threading.Barrier(num_threads)

    def worker(thread_idx):
        barrier.wait()
        for i in range(ops_per_thread):
            t_id = f"diag_{thread_idx}_op_{i}"
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

    print("Diagnostic completed. Total errors:", len(errors))
    for err in errors[:10]:
        print("Error detail:", err)
    if len(errors) > 10:
        print(f"... and {len(errors) - 10} more errors.")

if __name__ == "__main__":
    run_diagnostic()
