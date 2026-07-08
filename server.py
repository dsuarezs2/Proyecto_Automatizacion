import os
import sys
import json
import time
import mimetypes
from urllib.parse import parse_qs, urlparse
from http.server import HTTPServer, BaseHTTPRequestHandler

# Ensure current directory is in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Cargar variables de entorno (LangSmith, Gemini, etc.)
try:
    from dotenv import load_dotenv
    env_path = os.path.join(current_dir, ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
except ImportError:
    pass

from tests.utils import reset_inventory
from src.config import INVENTORY_PATH
from src.graph import TechServGraph, read_inventory

# In-memory session store to preserve shared memory state between interactive turns
SESSIONS = {}

class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Silence standard HTTP logging to keep console clean
        pass

    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query = parse_qs(parsed_url.query)
        
        # 1. API: Get stock details
        if path == "/api/inventory":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            inv = read_inventory()
            names_map = {
                "Pantalla_HP": "Pantalla HP Laptop 15",
                "RAM_8GB": "Memoria RAM DDR4 8GB",
                "RAM_16GB": "Memoria RAM DDR4 16GB",
                "Fuente_Poder": "Fuente de Poder 600W",
                "SSD_1TB": "SSD 1TB",
                "Mouse_Inalambrico": "Mouse Inalámbrico",
                "Teclado_Bluetooth": "Teclado Bluetooth",
                "Pasta_Termica": "Pasta Térmica",
                "Ventilador_CPU": "Ventilador CPU"
            }
            
            ui_inventory = {}
            for code, item in inv.items():
                ui_inventory[code] = {
                    "nombre": names_map.get(code, code),
                    "stock": item.get("stock", 0),
                    "precio": item.get("price", 0.0)
                }
                
            self.wfile.write(json.dumps(ui_inventory, ensure_ascii=False).encode("utf-8"))
            return

        # API: GET /api/status?thread_id=...
        if path == "/api/status":
            thread_id = query.get("thread_id", [None])[0]
            if not thread_id:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Missing thread_id parameter"}).encode("utf-8"))
                return
            
            from src.checkpointer import SQLiteCheckpointer
            checkpointer = SQLiteCheckpointer()
            res = checkpointer.load(thread_id)
            if not res:
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Thread {thread_id} not found"}).encode("utf-8"))
                return
            
            state, events = res
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"state": state, "events": events}, ensure_ascii=False).encode("utf-8"))
            return

        # API: GET /api/stream?thread_id=...
        if path == "/api/stream":
            thread_id = query.get("thread_id", [None])[0]
            if not thread_id:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Missing thread_id parameter"}).encode("utf-8"))
                return
            
            from src.checkpointer import SQLiteCheckpointer
            checkpointer = SQLiteCheckpointer()
            res = checkpointer.load(thread_id)
            if not res:
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Thread {thread_id} not found"}).encode("utf-8"))
                return
            
            state, _ = res
            transitions = state.get("node_transitions", [])
            
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            for transition in transitions:
                data_payload = json.dumps(transition, ensure_ascii=False)
                self.wfile.write(f"data: {data_payload}\n\n".encode("utf-8"))
                self.wfile.flush()
                time.sleep(0.01)
            self.close_connection = True
            return
            
        # 2. Serve static files
        if path == "/":
            path = "/index.html"
            
        clean_path = path.lstrip("/")
        file_path = os.path.join(current_dir, "dashboard", clean_path)
        
        if os.path.exists(file_path) and not os.path.isdir(file_path):
            mime_type, _ = mimetypes.guess_type(file_path)
            self.send_response(200)
            self.send_header("Content-Type", mime_type or "application/octet-stream")
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.end_headers()
            with open(file_path, "rb") as f:
                self.wfile.write(f.read())
        else:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"404 Not Found")

    def do_POST(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        if path == "/api/simulate":
            content_length = int(self.headers["Content-Length"])
            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8"))
            
            ticket_id = data.get("ticket_id") or data.get("thread_id") or f"TKT-WEB-{int(time.time())}"
            client_input = data.get("client_input", "").strip()
            reset_stock = data.get("reset_stock", False)
            
            import sqlite3
            from src.checkpointer import SQLiteCheckpointer
            checkpointer = SQLiteCheckpointer()
            
            if reset_stock:
                reset_inventory()
                SESSIONS.clear()
                checkpointer.reset_db()
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode("utf-8"))
                return
            
            # Setup session state from SQLite checkpointer
            res = checkpointer.load(ticket_id)
            if res:
                state, events = res
            else:
                state = {
                    "thread_id": ticket_id,
                    "ticket_id": ticket_id,
                    "cliente": {"nombre": "", "contacto": "", "canal_preferido": "email"},
                    "equipo": {"marca_modelo": "", "descripcion": "", "sintomas": []},
                    "tipo_solicitud": "",
                    "diagnostico": {
                        "falla_confirmada": "",
                        "repuestos_necesarios": [],
                        "costo_mano_obra": 0.0,
                        "tiempo_estimado_horas": 0,
                    },
                    "inventario_status": {},
                    "estado_ticket": "recibido",
                    "historial_conversacion": [],
                    "next_step": None,
                    "telemetry": {"latencies": {}, "tokens": {}},
                    "token_usage": {},
                    "mediation_cycles": 0,
                    "node_transitions": [],
                    "mcp_events": [],
                }
                events = []
                
            graph = TechServGraph()
            
            start_time = time.time()
            resume_decision = data.get("decision") or data.get("resume_decision")
            state, new_events, success = graph.execute(state, client_input, resume_decision=resume_decision)
            elapsed_time_ms = round((time.time() - start_time) * 1000, 2)
            
            for evt in new_events:
                if evt not in events:
                    events.append(evt)
            checkpointer.save(ticket_id, state, events)
            
            # Prepare telemetry summary
            conn = sqlite3.connect(checkpointer.db_path)
            total_tickets = 0
            successful_tickets = 0
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT state FROM checkpoints")
                rows = cursor.fetchall()
                total_tickets = len(rows)
                for row in rows:
                    st_val = json.loads(row[0])
                    if st_val.get("estado_ticket") in ["entregado", "venta_procesada", "resuelto_remoto"]:
                        successful_tickets += 1
            finally:
                conn.close()
            
            # Calcular tokens totales reales desde token_usage
            real_tokens = sum(state.get("token_usage", {}).values())
            telemetry_summary = {
                "total_tickets": total_tickets,
                "successful_tickets": successful_tickets,
                "success_rate": round(successful_tickets / total_tickets, 2) if total_tickets > 0 else 1.0,
                "total_tokens": real_tokens,
                "latencies": state.get("telemetry", {}).get("latencies", {}),
                "mediation_cycles": state.get("mediation_cycles", 0),
            }
            
            state_for_dashboard = {
                "ticket_id": state["ticket_id"],
                "cliente": state["cliente"],
                "tipo_solicitud": state["tipo_solicitud"],
                "equipo": state["equipo"],
                "diagnostico": state["diagnostico"],
                "inventario": state.get("inventario_status", {}),
                "estado_ticket": state["estado_ticket"],
                "historial_conversacion": state["historial_conversacion"],
                "next_step": state.get("next_step"),
                "telemetry": state.get("telemetry"),
                "node_transitions": state.get("node_transitions", [])
            }
            
            response_payload = {
                "ticket_id": ticket_id,
                "success": success,
                "state": state_for_dashboard,
                "events": events,
                "memory_history": [],
                "telemetry": telemetry_summary,
                "server_duration_ms": elapsed_time_ms
            }
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(response_payload, ensure_ascii=False).encode("utf-8"))
            return

        if path == "/api/resume":
            content_length = int(self.headers["Content-Length"])
            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8"))
            
            thread_id = data.get("thread_id") or data.get("ticket_id")
            decision = data.get("decision") or data.get("resume_decision") or "approved"
            
            if not thread_id:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Missing thread_id parameter"}).encode("utf-8"))
                return
            
            from src.checkpointer import SQLiteCheckpointer
            checkpointer = SQLiteCheckpointer()
            res = checkpointer.load(thread_id)
            if not res:
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Thread {thread_id} not found"}).encode("utf-8"))
                return
            
            state, events = res
            
            if not state.get("next_step"):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "state": state, "events": events}, ensure_ascii=False).encode("utf-8"))
                return

            graph = TechServGraph()
            state, new_events, success = graph.execute(state, client_input=decision, resume_decision=decision)
            
            for evt in new_events:
                if evt not in events:
                    events.append(evt)
            checkpointer.save(thread_id, state, events)
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"success": success, "state": state, "events": events}, ensure_ascii=False).encode("utf-8"))
            return
            
        self.send_response(404)
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

def run(server_class=HTTPServer, handler_class=DashboardHandler, port=8000):
    mimetypes.init()
    server_address = ("", port)
    httpd = server_class(server_address, handler_class)
    ls_active = bool(os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY"))
    print("\033[1;92m" + "="*80)
    print(f" SERVIDOR TECHSERV (LANGGRAPH + LANGSMITH) INICIADO EN: http://localhost:{port}")
    print(" Abre esta URL en tu navegador para ver la interfaz gráfica interactiva.")
    if ls_active:
        project = os.getenv("LANGSMITH_PROJECT", "TechServ-LangGraph")
        print(f" LangSmith activo — Traces en: https://smith.langchain.com (proyecto: {project})")
    print("="*80 + "\033[0m")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\033[91mServidor detenido por el usuario.\033[0m")
        httpd.server_close()

if __name__ == "__main__":
    reset_inventory()
    port = int(os.environ.get("PORT", 8000))
    run(port=port)
