import os
import sys
import unittest
import json
import time
import sqlite3
import urllib.request
import urllib.error
import threading
from http.server import ThreadingHTTPServer
from concurrent.futures import ThreadPoolExecutor, as_completed

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from tests.utils import reset_inventory, INVENTORY_PATH
from src.graph import TechServGraph, read_inventory
from src.checkpointer import SQLiteCheckpointer
from server import DashboardHandler

def find_free_port():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port

def http_post(url, data):
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, {"error": e.reason}

class TestParallelE2EPressure(unittest.TestCase):
    port = None
    server = None
    server_thread = None

    @classmethod
    def setUpClass(cls):
        # We start a ThreadingHTTPServer to enable true parallel request processing
        cls.port = find_free_port()
        cls.server = ThreadingHTTPServer(("127.0.0.1", cls.port), DashboardHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        time.sleep(0.2)

    @classmethod
    def tearDownClass(cls):
        if cls.server:
            cls.server.shutdown()
            cls.server.server_close()
        if cls.server_thread:
            cls.server_thread.join()

    def setUp(self):
        reset_inventory()
        self.checkpointer = SQLiteCheckpointer()
        conn = sqlite3.connect(self.checkpointer.db_path)
        try:
            conn.execute("DELETE FROM checkpoints")
            conn.commit()
        finally:
            conn.close()

    def test_parallel_simulation_and_resume_pressure(self):
        """
        Verify that parallel execution functions correctly under concurrent pressure
        by executing 10 concurrent simulation requests followed by 10 concurrent resumes.
        """
        url_simulate = f"http://127.0.0.1:{self.port}/api/simulate"
        url_resume = f"http://127.0.0.1:{self.port}/api/resume"
        
        num_requests = 10
        errors = []
        latencies = []

        # Step 1: Concurrent Simulations
        print(f"\nSending {num_requests} concurrent simulate requests...")
        with ThreadPoolExecutor(max_workers=num_requests) as executor:
            futures = []
            for i in range(num_requests):
                ticket_id = f"T4C4_PRES_{i}"
                payload = {
                    "ticket_id": ticket_id,
                    "client_input": f"Hola, soy Carlos {i}. Mi laptop HP tiene la pantalla rota."
                }
                
                def make_request(p, t_id):
                    t_start = time.perf_counter()
                    status, res = http_post(url_simulate, p)
                    t_end = time.perf_counter()
                    return status, res, t_end - t_start, t_id
                    
                futures.append(executor.submit(make_request, payload, ticket_id))

            for f in as_completed(futures):
                try:
                    status, res, latency, t_id = f.result()
                    latencies.append(latency)
                    if status != 200:
                        errors.append(f"Simulate {t_id} failed with status {status}: {res}")
                    elif res.get("state", {}).get("cliente", {}).get("nombre") != "Carlos Pérez":
                        errors.append(f"Simulate {t_id} returned incorrect client name: {res}")
                except Exception as e:
                    errors.append(f"Simulate request failed with exception: {type(e).__name__}: {str(e)}")

        # Step 2: Concurrent Resumes
        print(f"Sending {num_requests} concurrent resume (approval) requests...")
        with ThreadPoolExecutor(max_workers=num_requests) as executor:
            futures = []
            for i in range(num_requests):
                thread_id = f"T4C4_PRES_{i}"
                payload = {
                    "thread_id": thread_id,
                    "decision": "approved"
                }
                
                def make_request(p, t_id):
                    t_start = time.perf_counter()
                    status, res = http_post(url_resume, p)
                    t_end = time.perf_counter()
                    return status, res, t_end - t_start, t_id
                    
                futures.append(executor.submit(make_request, payload, thread_id))

            for f in as_completed(futures):
                try:
                    status, res, latency, t_id = f.result()
                    latencies.append(latency)
                    if status != 200:
                        errors.append(f"Resume {t_id} failed with status {status}: {res}")
                    else:
                        actual_state = res.get("state", {}).get("estado_ticket")
                        if actual_state not in ["entregado", "cancelado"]:
                            errors.append(f"Resume {t_id} returned unexpected status: {actual_state}")
                except Exception as e:
                    errors.append(f"Resume request failed with exception: {type(e).__name__}: {str(e)}")

        # Report stats
        total_requests = len(latencies)
        success_rate = (total_requests - len(errors)) / total_requests * 100
        avg_latency = sum(latencies) / total_requests if latencies else 0
        min_latency = min(latencies) if latencies else 0
        max_latency = max(latencies) if latencies else 0

        print(f"\n--- Concurrency Pressure Stats ---")
        print(f"Success Rate: {success_rate:.2f}% ({total_requests - len(errors)}/{total_requests})")
        print(f"Average Latency: {avg_latency * 1000:.2f} ms")
        print(f"Min Latency: {min_latency * 1000:.2f} ms")
        print(f"Max Latency: {max_latency * 1000:.2f} ms")
        
        self.assertEqual(len(errors), 0, f"Errors under E2E pressure: {errors}")
