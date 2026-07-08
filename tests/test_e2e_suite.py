import os
import sys
import unittest
import json
import time
import sqlite3
import urllib.request
import urllib.error
import threading
from http.server import HTTPServer

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from tests.utils import reset_inventory, INVENTORY_PATH
from src.graph import TechServGraph, read_inventory, write_inventory
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
    with urllib.request.urlopen(req) as response:
        return response.status, json.loads(response.read().decode("utf-8"))

def http_get(url):
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req) as response:
        return response.status, response.read().decode("utf-8")

class TestE2ESuite(unittest.TestCase):
    port = None
    server = None
    server_thread = None

    @classmethod
    def setUpClass(cls):
        cls.port = find_free_port()
        cls.server = HTTPServer(("127.0.0.1", cls.port), DashboardHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        # Give server a moment to start
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        if cls.server:
            cls.server.shutdown()
            cls.server.server_close()
        if cls.server_thread:
            cls.server_thread.join()

    def setUp(self):
        reset_inventory()
        checkpointer = SQLiteCheckpointer()
        conn = sqlite3.connect(checkpointer.db_path)
        try:
            conn.execute("DELETE FROM checkpoints")
            conn.commit()
        finally:
            conn.close()

    # Helpers
    def simulate(self, ticket_id, client_input, decision=None):
        url = f"http://127.0.0.1:{self.port}/api/simulate"
        payload = {
            "ticket_id": ticket_id,
            "client_input": client_input,
            "decision": decision
        }
        return http_post(url, payload)

    def resume(self, thread_id, decision):
        url = f"http://127.0.0.1:{self.port}/api/resume"
        payload = {
            "thread_id": thread_id,
            "decision": decision
        }
        return http_post(url, payload)

    def get_status(self, thread_id):
        url = f"http://127.0.0.1:{self.port}/api/status?thread_id={thread_id}"
        status, data_str = http_get(url)
        return status, json.loads(data_str)

    def get_stream(self, thread_id):
        url = f"http://127.0.0.1:{self.port}/api/stream?thread_id={thread_id}"
        status, data_str = http_get(url)
        return status, data_str

    # ----------------------------------------------------
    # TIER 1 - Happy Path (45 cases)
    # ----------------------------------------------------
    
    # Feature 1: Customer Service / Slot Filling (5 tests)
    def test_tier1_feat1_case1(self):
        status, res = self.simulate("T1F1C1", "Hola, soy Carlos Pérez, mi cel es +5491133334444 y prefiero whatsapp. Mi laptop HP tiene la pantalla rota.")
        self.assertEqual(status, 200)
        self.assertEqual(res["state"]["cliente"]["nombre"], "Carlos Pérez")
        self.assertEqual(res["state"]["cliente"]["canal_preferido"], "whatsapp")

    def test_tier1_feat1_case2(self):
        status, res = self.simulate("T1F1C2", "Buenas, soy Sofía Gómez, mi email es sofia@gmail.com, celular +5491155556666, prefiero sms. Mi PC gamer de escritorio no arranca para nada.")
        self.assertEqual(status, 200)
        self.assertEqual(res["state"]["cliente"]["nombre"], "Sofía Gómez")
        self.assertEqual(res["state"]["cliente"]["canal_preferido"], "sms")

    def test_tier1_feat1_case3(self):
        # Lucia flow slot filling E2E
        self.simulate("T1F1C3", "Hola soy Lucía y mi compu no anda")
        status, res = self.simulate("T1F1C3", "Es una Dell Inspiron que se calienta, mi email es lucia@outlook.com y prefiero email")
        self.assertEqual(status, 200)
        self.assertEqual(res["state"]["cliente"]["nombre"], "Lucía")
        self.assertEqual(res["state"]["cliente"]["canal_preferido"], "email")

    def test_tier1_feat1_case4(self):
        status, res = self.simulate("T1F1C4", "Hola, soy Alejandro Ruiz, mi email es al@gmail.com, prefiero email. Quiero comprar un SSD 1TB.")
        self.assertEqual(status, 200)
        self.assertEqual(res["state"]["cliente"]["nombre"], "Alejandro Ruiz")
        self.assertEqual(res["state"]["cliente"]["canal_preferido"], "email")

    def test_tier1_feat1_case5(self):
        status, res = self.simulate("T1F1C5", "Hola, soy Mateo Torres, mi cel es +5491188887777 y prefiero whatsapp. Mi tablet con teclado Lenovo bluetooth no vincula.")
        self.assertEqual(status, 200)
        self.assertEqual(res["state"]["cliente"]["nombre"], "Mateo Torres")
        self.assertEqual(res["state"]["cliente"]["canal_preferido"], "whatsapp")

    # Feature 2: Request Classification (5 tests)
    def test_tier1_feat2_case1(self):
        status, res = self.simulate("T1F2C1", "Carlos Pérez HP screen broken")
        self.assertEqual(res["state"]["tipo_solicitud"], "reparacion")

    def test_tier1_feat2_case2(self):
        status, res = self.simulate("T1F2C2", "Sofía Gómez PC gamer no arranca")
        self.assertEqual(res["state"]["tipo_solicitud"], "reparacion")

    def test_tier1_feat2_case3(self):
        status, res = self.simulate("T1F2C3", "Alejandro Ruiz compra SSD 1TB")
        self.assertEqual(res["state"]["tipo_solicitud"], "venta")

    def test_tier1_feat2_case4(self):
        status, res = self.simulate("T1F2C4", "Mateo Torres tablet teclado bluetooth no responde")
        self.assertEqual(res["state"]["tipo_solicitud"], "soporte")

    def test_tier1_feat2_case5(self):
        status, res = self.simulate("T1F2C5", "Hola soy Lucía y mi compu no anda")
        self.assertEqual(res["state"]["tipo_solicitud"], "ambiguo")

    # Feature 3: Ambiguity Resolution (5 tests)
    def test_tier1_feat3_case1(self):
        status, res = self.simulate("T1F3C1", "mi compu no anda")
        self.assertEqual(res["state"]["tipo_solicitud"], "ambiguo")
        self.assertEqual(res["state"]["next_step"], "pedir_aclaracion")

    def test_tier1_feat3_case2(self):
        self.simulate("T1F3C2", "Hola soy Lucía y mi compu no anda")
        status, res = self.simulate("T1F3C2", "Es una Dell Inspiron que se calienta, mi email es lucia@outlook.com y prefiero email")
        self.assertEqual(res["state"]["tipo_solicitud"], "reparacion")
        self.assertEqual(res["state"]["next_step"], "reparar_equipo")

    def test_tier1_feat3_case3(self):
        # Empty input should trigger support/fallback
        status, res = self.simulate("T1F3C3", "   ")
        self.assertEqual(res["state"]["tipo_solicitud"], "soporte")

    def test_tier1_feat3_case4(self):
        # Vague greeting should be classified as support
        status, res = self.simulate("T1F3C4", "Hola")
        self.assertEqual(res["state"]["tipo_solicitud"], "soporte")

    def test_tier1_feat3_case5(self):
        status, res = self.simulate("T1F3C5", "Hola soy Lucía y mi compu no anda")
        # Clarification prompt must request model/brand
        clarification_msg = res["state"]["historial_conversacion"][-1]["content"]
        self.assertIn("marca y modelo", clarification_msg.lower())

    # Feature 4: Technical Diagnosis (5 tests)
    def test_tier1_feat4_case1(self):
        status, res = self.simulate("T1F4C1", "Carlos Pérez HP screen broken")
        self.assertEqual(res["state"]["diagnostico"]["falla_confirmada"], "Pantalla rota")

    def test_tier1_feat4_case2(self):
        status, res = self.simulate("T1F4C2", "Sofía Gómez PC gamer no arranca")
        self.assertEqual(res["state"]["diagnostico"]["falla_confirmada"], "No arranca (Falla en Fuente y RAM)")

    def test_tier1_feat4_case3(self):
        self.simulate("T1F4C3", "Hola soy Lucía y mi compu no anda")
        status, res = self.simulate("T1F4C3", "Es una Dell Inspiron que se calienta, mi email es lucia@outlook.com y prefiero email")
        self.assertEqual(res["state"]["diagnostico"]["falla_confirmada"], "Sobrecalentamiento")

    def test_tier1_feat4_case4(self):
        status, res = self.simulate("T1F4C4", "Alejandro Ruiz compra SSD 1TB")
        self.assertEqual(res["state"]["diagnostico"]["falla_confirmada"], "Compra directa de repuesto")

    def test_tier1_feat4_case5(self):
        status, res = self.simulate("T1F4C5", "Mateo Torres tablet teclado bluetooth")
        self.assertEqual(res["state"]["diagnostico"]["falla_confirmada"], "Problema de vinculación bluetooth")

    # Feature 5: Inventory Management (5 tests)
    def test_tier1_feat5_case1(self):
        # Carlos HP screen is 3 in baseline.
        status, res = self.simulate("T1F5C1", "Carlos Pérez HP screen broken")
        inv = read_inventory()
        self.assertEqual(inv["Pantalla_HP"]["stock"], 2)

    def test_tier1_feat5_case2(self):
        # Sofia gamer PC needs Fuente_Poder (baseline: 2) and RAM_16GB (baseline: 5)
        status, res = self.simulate("T1F5C2", "Sofía Gómez PC gamer no arranca")
        inv = read_inventory()
        self.assertEqual(inv["Fuente_Poder"]["stock"], 1)

    def test_tier1_feat5_case3(self):
        # Alejandro buys SSD 1TB (baseline: 5)
        status, res = self.simulate("T1F5C3", "Alejandro Ruiz compra SSD 1TB")
        inv = read_inventory()
        self.assertEqual(inv["SSD_1TB"]["stock"], 4)

    def test_tier1_feat5_case4(self):
        # Lucia needs Pasta_Termica (baseline: 20) and Ventilador_CPU (baseline: 15)
        self.simulate("T1F5C4", "Hola soy Lucía y mi compu no anda")
        self.simulate("T1F5C4", "Es una Dell Inspiron que se calienta, mi email es lucia@outlook.com y prefiero email")
        inv = read_inventory()
        self.assertEqual(inv["Pasta_Termica"]["stock"], 19)

    def test_tier1_feat5_case5(self):
        self.simulate("T1F5C5", "Hola soy Lucía y mi compu no anda")
        self.simulate("T1F5C5", "Es una Dell Inspiron que se calienta, mi email es lucia@outlook.com y prefiero email")
        inv = read_inventory()
        self.assertEqual(inv["Ventilador_CPU"]["stock"], 14)

    # Feature 6: Stock Mediation (5 tests)
    def test_tier1_feat6_case1(self):
        # RAM_8GB is out of stock in baseline
        inv = read_inventory()
        self.assertEqual(inv["RAM_8GB"]["stock"], 0)

    def test_tier1_feat6_case2(self):
        status, res = self.simulate("T1F6C2", "Sofía Gómez PC gamer no arranca")
        # Verify RAM_16GB was suggested instead of RAM_8GB
        self.assertIn("RAM_16GB", res["state"]["diagnostico"]["repuestos_necesarios"])
        self.assertNotIn("RAM_8GB", res["state"]["diagnostico"]["repuestos_necesarios"])

    def test_tier1_feat6_case3(self):
        status, res = self.simulate("T1F6C3", "Sofía Gómez PC gamer no arranca")
        # Check stock verification status for RAM_16GB
        self.assertTrue(res["state"]["inventario"]["RAM_16GB"]["disponible"])

    def test_tier1_feat6_case4(self):
        status, res = self.simulate("T1F6C4", "Sofía Gómez PC gamer no arranca")
        # Event ticket.error about out of stock RAM_8GB must be created
        events = res["events"]
        out_of_stock_evt = [e for e in events if e["evento"] == "ticket.error"]
        self.assertTrue(len(out_of_stock_evt) > 0)
        self.assertIn("Sin stock de RAM_8GB", out_of_stock_evt[0]["payload"]["error"])

    def test_tier1_feat6_case5(self):
        status, res = self.simulate("T1F6C5", "Sofía Gómez PC gamer no arranca")
        # Check inventory is decremented for suggested alternative RAM_16GB
        inv = read_inventory()
        self.assertEqual(inv["RAM_16GB"]["stock"], 4)

    # Feature 7: Budget Orchestration (5 tests)
    def test_tier1_feat7_case1(self):
        # Carlos: $120 part + $50 labor = $170
        status, res = self.simulate("T1F7C1", "Carlos Pérez HP screen broken")
        total = sum(v["precio"] for v in res["state"]["inventario"].values()) + res["state"]["diagnostico"]["costo_mano_obra"]
        self.assertEqual(total, 170.0)

    def test_tier1_feat7_case2(self):
        # Sofía: $90 + $80 + $50 = $220
        status, res = self.simulate("T1F7C2", "Sofía Gómez PC gamer no arranca")
        total = sum(v["precio"] for v in res["state"]["inventario"].values()) + res["state"]["diagnostico"]["costo_mano_obra"]
        self.assertEqual(total, 220.0)

    def test_tier1_feat7_case3(self):
        # Lucía: $15 + $20 + $40 = $75
        self.simulate("T1F7C3", "Hola soy Lucía y mi compu no anda")
        status, res = self.simulate("T1F7C3", "Es una Dell Inspiron que se calienta, mi email es lucia@outlook.com y prefiero email")
        total = sum(v["precio"] for v in res["state"]["inventario"].values()) + res["state"]["diagnostico"]["costo_mano_obra"]
        self.assertEqual(total, 75.0)

    def test_tier1_feat7_case4(self):
        # Alejandro: $99.0 total
        status, res = self.simulate("T1F7C4", "Alejandro Ruiz compra SSD 1TB")
        total = sum(v["precio"] for v in res["state"]["inventario"].values())
        self.assertEqual(total, 99.0)

    def test_tier1_feat7_case5(self):
        # Mateo: $0
        status, res = self.simulate("T1F7C5", "Mateo Torres tablet teclado bluetooth")
        total = sum(v["precio"] for v in res["state"]["inventario"].values()) + res["state"]["diagnostico"]["costo_mano_obra"]
        self.assertEqual(total, 0.0)

    # Feature 8: Notification Delivery (5 tests)
    def test_tier1_feat8_case1(self):
        status, res = self.simulate("T1F8C1", "Carlos Pérez HP screen broken")
        notif_events = [e for e in res["events"] if e["evento"] == "cliente.notificado"]
        self.assertTrue(len(notif_events) > 0)
        self.assertEqual(notif_events[0]["payload"]["canal"], "whatsapp")

    def test_tier1_feat8_case2(self):
        status, res = self.simulate("T1F8C2", "Sofía Gómez PC gamer no arranca")
        notif_events = [e for e in res["events"] if e["evento"] == "cliente.notificado"]
        self.assertTrue(len(notif_events) > 0)
        self.assertEqual(notif_events[0]["payload"]["canal"], "sms")

    def test_tier1_feat8_case3(self):
        self.simulate("T1F8C3", "Hola soy Lucía y mi compu no anda")
        status, res = self.simulate("T1F8C3", "Es una Dell Inspiron que se calienta, mi email es lucia@outlook.com y prefiero email")
        notif_events = [e for e in res["events"] if e["evento"] == "cliente.notificado"]
        self.assertTrue(len(notif_events) > 0)
        self.assertEqual(notif_events[0]["payload"]["canal"], "email")

    def test_tier1_feat8_case4(self):
        status, res = self.simulate("T1F8C4", "Alejandro Ruiz compra SSD 1TB")
        notif_events = [e for e in res["events"] if e["evento"] == "cliente.notificado"]
        self.assertTrue(len(notif_events) > 0)
        self.assertEqual(notif_events[0]["payload"]["canal"], "email")

    def test_tier1_feat8_case5(self):
        status, res = self.simulate("T1F8C5", "Mateo Torres tablet teclado bluetooth")
        notif_events = [e for e in res["events"] if e["evento"] == "cliente.notificado"]
        self.assertTrue(len(notif_events) > 0)
        self.assertEqual(notif_events[0]["payload"]["canal"], "whatsapp")

    # Feature 9: Interrupt & Resume (5 tests)
    def test_tier1_feat9_case1(self):
        status, res = self.simulate("T1F9C1", "Carlos Pérez HP screen broken")
        self.assertEqual(res["state"]["next_step"], "reparar_equipo")

    def test_tier1_feat9_case2(self):
        status, res = self.simulate("T1F9C2", "Sofía Gómez PC gamer no arranca")
        self.assertEqual(res["state"]["next_step"], "reparar_equipo")

    def test_tier1_feat9_case3(self):
        self.simulate("T1F9C3", "Carlos Pérez HP screen broken")
        status, res = self.resume("T1F9C3", "approved")
        self.assertEqual(res["state"]["estado_ticket"], "entregado")
        self.assertIsNone(res["state"]["next_step"])

    def test_tier1_feat9_case4(self):
        self.simulate("T1F9C4", "Sofía Gómez PC gamer no arranca")
        status, res = self.resume("T1F9C4", "approved")
        self.assertEqual(res["state"]["estado_ticket"], "entregado")
        self.assertIsNone(res["state"]["next_step"])

    def test_tier1_feat9_case5(self):
        self.simulate("T1F9C5", "Carlos Pérez HP screen broken")
        # Stock should be 2 after reservation
        inv = read_inventory()
        self.assertEqual(inv["Pantalla_HP"]["stock"], 2)
        # Reject the resume
        status, res = self.resume("T1F9C5", "rejected")
        self.assertEqual(res["state"]["estado_ticket"], "cancelado")
        # Stock should be released back to 3
        inv = read_inventory()
        self.assertEqual(inv["Pantalla_HP"]["stock"], 3)

    # ----------------------------------------------------
    # TIER 2 - Boundary & Corner Cases (45 cases)
    # ----------------------------------------------------

    # Feature 1: Customer Service / Slot Filling
    def test_tier2_feat1_case1(self):
        # Missing contact details: should parse name but fallback preferred channel to email
        status, res = self.simulate("T2F1C1", "Carlos Pérez HP screen broken")
        self.assertEqual(res["state"]["cliente"]["nombre"], "Carlos Pérez")
        self.assertEqual(res["state"]["cliente"]["canal_preferido"], "email")

    def test_tier2_feat1_case2(self):
        # Very long name
        long_name = "Carlos " + "A" * 100 + " Perez"
        status, res = self.simulate("T2F1C2", f"{long_name} HP screen broken")
        self.assertIn("Carlos", res["state"]["cliente"]["nombre"])

    def test_tier2_feat1_case3(self):
        # Special characters in name
        status, res = self.simulate("T2F1C3", "Carlos Pérez-Gómez HP screen broken")
        self.assertEqual(res["state"]["cliente"]["nombre"], "Carlos Pérez-Gómez")

    def test_tier2_feat1_case4(self):
        # Invalid preferred channel fallback to email
        status, res = self.simulate("T2F1C4", "Carlos Pérez HP screen broken, prefiero señales de humo")
        self.assertEqual(res["state"]["cliente"]["canal_preferido"], "email")

    def test_tier2_feat1_case5(self):
        # Leading/trailing spaces in name
        status, res = self.simulate("T2F1C5", "   Carlos Pérez   HP screen broken")
        self.assertEqual(res["state"]["cliente"]["nombre"], "Carlos Pérez")

    # Feature 2: Request Classification
    def test_tier2_feat2_case1(self):
        # Multiple keywords - repair & sales
        status, res = self.simulate("T2F2C1", "Hola Carlos Pérez quiero reparar mi HP y comprar un SSD 1TB")
        # Repair should be prioritized based on severity
        self.assertEqual(res["state"]["tipo_solicitud"], "reparacion")

    def test_tier2_feat2_case2(self):
        # Whitespace input defaults to soporte
        status, res = self.simulate("T2F2C2", "      ")
        self.assertEqual(res["state"]["tipo_solicitud"], "soporte")

    def test_tier2_feat2_case3(self):
        # Uppercase input
        status, res = self.simulate("T2F2C3", "CARLOS PEREZ HP SCREEN BROKEN")
        self.assertEqual(res["state"]["tipo_solicitud"], "reparacion")

    def test_tier2_feat2_case4(self):
        # Emoji only defaults to soporte
        status, res = self.simulate("T2F2C4", "💻🔥🛑")
        self.assertEqual(res["state"]["tipo_solicitud"], "soporte")

    def test_tier2_feat2_case5(self):
        # Spanish accents in keywords
        status, res = self.simulate("T2F2C5", "Hola, soy Sofía Gómez, mi PC gamer no arránca")
        self.assertEqual(res["state"]["tipo_solicitud"], "reparacion")

    # Feature 3: Ambiguity Resolution
    def test_tier2_feat3_case1(self):
        # Name only -> ambiguous
        status, res = self.simulate("T2F3C1", "Hola, soy Carlos Pérez")
        self.assertEqual(res["state"]["tipo_solicitud"], "ambiguo")

    def test_tier2_feat3_case2(self):
        # Symptom only without client name -> ambiguous
        status, res = self.simulate("T2F3C2", "mi laptop Dell no anda")
        self.assertEqual(res["state"]["tipo_solicitud"], "ambiguo")

    def test_tier2_feat3_case3(self):
        # Double ambiguous input -> stays ambiguous
        self.simulate("T2F3C3", "hola")
        status, res = self.simulate("T2F3C3", "como andas")
        self.assertEqual(res["state"]["tipo_solicitud"], "ambiguo")

    def test_tier2_feat3_case4(self):
        # Cancellation during ambiguity -> support/resolved
        self.simulate("T2F3C4", "hola soy Carlos")
        status, res = self.simulate("T2F3C4", "ya no necesito soporte, gracias")
        self.assertEqual(res["state"]["tipo_solicitud"], "soporte")

    def test_tier2_feat3_case5(self):
        # Verify checkpointer saves ambiguous turns
        self.simulate("T2F3C5", "Hola soy Lucía y mi compu no anda")
        status, data = self.get_status("T2F3C5")
        self.assertEqual(data["state"]["tipo_solicitud"], "ambiguo")

    # Feature 4: Technical Diagnosis
    def test_tier2_feat4_case1(self):
        # Free remote support diagnosis has zero labor cost
        status, res = self.simulate("T2F4C1", "Mateo Torres tablet teclado bluetooth")
        self.assertEqual(res["state"]["diagnostico"]["costo_mano_obra"], 0.0)

    def test_tier2_feat4_case2(self):
        # Verify estimated hours is non-negative
        status, res = self.simulate("T2F4C2", "Carlos Pérez HP screen broken")
        self.assertTrue(res["state"]["diagnostico"]["tiempo_estimado_horas"] >= 0)

    def test_tier2_feat4_case3(self):
        # Empty symptoms list in input for sales
        status, res = self.simulate("T2F4C3", "Alejandro Ruiz compra SSD 1TB")
        self.assertEqual(len(res["state"]["equipo"]["sintomas"]), 0)

    def test_tier2_feat4_case4(self):
        # Unknown symptoms mapped to support
        status, res = self.simulate("T2F4C4", "Mi computador hace ruidos de ovni")
        self.assertEqual(res["state"]["tipo_solicitud"], "soporte")

    def test_tier2_feat4_case5(self):
        # Confirm Pydantic validation structure in result
        status, res = self.simulate("T2F4C5", "Carlos Pérez HP screen broken")
        self.assertIn("falla_confirmada", res["state"]["diagnostico"])

    # Feature 5: Inventory Management
    def test_tier2_feat5_case1(self):
        # Check stock of unknown items returns False/Empty status
        status, res = self.simulate("T2F5C1", "Quiero comprar una Taza de Cafe")
        # Classified as support or purchase but not in standard inventory status
        self.assertNotIn("Taza_de_Cafe", res["state"]["inventario"])

    def test_tier2_feat5_case2(self):
        # Stock decrement when stock is 1
        # Set stock of Pantalla_HP to 1
        inv = read_inventory()
        inv["Pantalla_HP"]["stock"] = 1
        write_inventory(inv)
        status, res = self.simulate("T2F5C2", "Carlos Pérez HP screen broken")
        inv_after = read_inventory()
        self.assertEqual(inv_after["Pantalla_HP"]["stock"], 0)

    def test_tier2_feat5_case3(self):
        # Stock check for empty code handles gracefully
        status, res = self.simulate("T2F5C3", "Hola, quiero reparar algo")
        self.assertEqual(res["state"]["tipo_solicitud"], "soporte")

    def test_tier2_feat5_case4(self):
        # Double reservation on same ticket should only decrement once
        self.simulate("T2F5C4", "Carlos Pérez HP screen broken")
        inv = read_inventory()
        stock_1 = inv["Pantalla_HP"]["stock"]
        # Call simulate again
        self.simulate("T2F5C4", "Carlos Pérez HP screen broken")
        inv2 = read_inventory()
        self.assertEqual(inv2["Pantalla_HP"]["stock"], stock_1)

    def test_tier2_feat5_case5(self):
        # Manual inventory update reflected in new ticket simulation
        inv = read_inventory()
        inv["SSD_1TB"]["stock"] = 10
        write_inventory(inv)
        status, res = self.simulate("T2F5C5", "Alejandro Ruiz compra SSD 1TB")
        inv2 = read_inventory()
        self.assertEqual(inv2["SSD_1TB"]["stock"], 9)

    # Feature 6: Stock Mediation
    def test_tier2_feat6_case1(self):
        # If alternative RAM_16GB is also out of stock
        inv = read_inventory()
        inv["RAM_8GB"]["stock"] = 0
        inv["RAM_16GB"]["stock"] = 0
        write_inventory(inv)
        
        status, res = self.simulate("T2F6C1", "Sofía Gómez PC gamer no arranca")
        # Stays in budget state but alternative marked unavailable
        self.assertFalse(res["state"]["inventario"]["RAM_16GB"]["disponible"])

    def test_tier2_feat6_case2(self):
        # Mediation with no alternative suggested
        status, res = self.simulate("T2F6C2", "Carlos Pérez HP screen broken")
        # No alternative should be suggested for screen
        self.assertEqual(res["state"]["diagnostico"]["repuestos_necesarios"], ["Pantalla_HP"])

    def test_tier2_feat6_case3(self):
        # Mediation with multiple out-of-stock items (Fuente and RAM)
        inv = read_inventory()
        inv["Fuente_Poder"]["stock"] = 0
        inv["RAM_8GB"]["stock"] = 0
        write_inventory(inv)
        status, res = self.simulate("T2F6C3", "Sofía Gómez PC gamer no arranca")
        # Fuente_Poder should be marked unavailable
        self.assertFalse(res["state"]["inventario"]["Fuente_Poder"]["disponible"])

    def test_tier2_feat6_case4(self):
        # Verify budget total is updated during mediation
        status, res = self.simulate("T2F6C4", "Sofía Gómez PC gamer no arranca")
        # Total cost is sum of components
        total = sum(v["precio"] for v in res["state"]["inventario"].values()) + res["state"]["diagnostico"]["costo_mano_obra"]
        self.assertEqual(total, 220.0)

    def test_tier2_feat6_case5(self):
        # Mediation state check pointer saved
        self.simulate("T2F6C5", "Sofía Gómez PC gamer no arranca")
        status, data = self.get_status("T2F6C5")
        self.assertIn("RAM_16GB", data["state"]["diagnostico"]["repuestos_necesarios"])

    # Feature 7: Budget Orchestration
    def test_tier2_feat7_case1(self):
        # Free remote support budget
        status, res = self.simulate("T2F7C1", "Mateo Torres tablet teclado bluetooth")
        total = sum(v["precio"] for v in res["state"]["inventario"].values()) + res["state"]["diagnostico"]["costo_mano_obra"]
        self.assertEqual(total, 0.0)

    def test_tier2_feat7_case2(self):
        # High price part budget
        inv = read_inventory()
        inv["SSD_1TB"]["price"] = 1000.0
        write_inventory(inv)
        status, res = self.simulate("T2F7C2", "Alejandro Ruiz compra SSD 1TB")
        # Final price discount 10%
        self.assertEqual(res["state"]["inventario"]["SSD_1TB"]["precio"], 900.0)

    def test_tier2_feat7_case3(self):
        # Budget total with float labor cost
        status, res = self.simulate("T2F7C3", "Carlos Pérez HP screen broken")
        self.assertTrue(isinstance(res["state"]["diagnostico"]["costo_mano_obra"], float))

    def test_tier2_feat7_case4(self):
        # Budget format check: ensure positive values
        status, res = self.simulate("T2F7C4", "Carlos Pérez HP screen broken")
        self.assertTrue(res["state"]["diagnostico"]["costo_mano_obra"] > 0)

    def test_tier2_feat7_case5(self):
        # Handle negative part price boundary gracefully
        inv = read_inventory()
        inv["Pantalla_HP"]["price"] = -10.0
        write_inventory(inv)
        status, res = self.simulate("T2F7C5", "Carlos Pérez HP screen broken")
        self.assertEqual(res["state"]["inventario"]["Pantalla_HP"]["precio"], -10.0)

    # Feature 8: Notification Delivery
    def test_tier2_feat8_case1(self):
        # Send notification even with short symptom
        status, res = self.simulate("T2F8C1", "Carlos HP broken")
        notif_evts = [e for e in res["events"] if e["evento"] == "cliente.notificado"]
        self.assertTrue(len(notif_evts) > 0)

    def test_tier2_feat8_case2(self):
        # Invalid email format (should still process ticket)
        status, res = self.simulate("T2F8C2", "Sofía Gómez email sofia@gmail PC gamer no arranca")
        self.assertEqual(status, 200)

    def test_tier2_feat8_case3(self):
        # Fallback preferred channel
        status, res = self.simulate("T2F8C3", "Carlos Pérez HP screen broken, prefiero fax")
        # Default channel WhatsApp/Email fallback
        notif_evts = [e for e in res["events"] if e["evento"] == "cliente.notificado"]
        self.assertEqual(res["state"]["cliente"]["canal_preferido"], "email")

    def test_tier2_feat8_case4(self):
        # Verify conversational history length grows
        status, res = self.simulate("T2F8C4", "Carlos Pérez HP screen broken")
        self.assertTrue(len(res["state"]["historial_conversacion"]) > 0)

    def test_tier2_feat8_case5(self):
        # Notification logs check pointer load
        self.simulate("T2F8C5", "Carlos Pérez HP screen broken")
        status, data = self.get_status("T2F8C5")
        self.assertTrue(len(data["state"]["historial_conversacion"]) > 0)

    # Feature 9: Interrupt & Resume
    def test_tier2_feat9_case1(self):
        # Resume with custom/alternate decision approval text (e.g. "Si, por favor")
        self.simulate("T2F9C1", "Carlos Pérez HP screen broken")
        status, res = self.resume("T2F9C1", "Si, por favor")
        self.assertEqual(res["state"]["estado_ticket"], "entregado")

    def test_tier2_feat9_case2(self):
        # Resume non-existent or not paused thread returns error or fails
        status, res = self.resume("T2F9C2", "approved")
        self.assertEqual(status, 404)

    def test_tier2_feat9_case3(self):
        # Double resume check: second resume works or handles gracefully
        self.simulate("T2F9C3", "Carlos Pérez HP screen broken")
        self.resume("T2F9C3", "approved")
        status, res = self.resume("T2F9C3", "approved")
        self.assertEqual(res["state"]["estado_ticket"], "entregado")

    def test_tier2_feat9_case4(self):
        # Resume after delete from DB yields 404
        self.simulate("T2F9C4", "Carlos Pérez HP screen broken")
        checkpointer = SQLiteCheckpointer()
        conn = sqlite3.connect(checkpointer.db_path)
        try:
            conn.execute("DELETE FROM checkpoints WHERE thread_id = 'T2F9C4'")
            conn.commit()
        finally:
            conn.close()
        status, res = self.resume("T2F9C4", "approved")
        self.assertEqual(status, 404)

    def test_tier2_feat9_case5(self):
        # Resume with default/empty decision defaults to approved
        self.simulate("T2F9C5", "Carlos Pérez HP screen broken")
        status, res = self.resume("T2F9C5", "")
        self.assertEqual(res["state"]["estado_ticket"], "entregado")

    # ----------------------------------------------------
    # TIER 3 - Cross-Feature Combinations (9 cases)
    # ----------------------------------------------------
    def test_tier3_case1(self):
        # Support escalates to repair (not implemented physically, but support flow returns resuelto_remoto)
        status, res = self.simulate("T3C1", "Mateo Torres tablet teclado bluetooth")
        self.assertEqual(res["state"]["tipo_solicitud"], "soporte")
        self.assertEqual(res["state"]["estado_ticket"], "resuelto_remoto")

    def test_tier3_case2(self):
        # Ambiguous input turns into Sales after slot filling
        self.simulate("T3C2", "Hola soy Alejandro Ruiz y quiero comprar algo")
        status, res = self.simulate("T3C2", "Quiero comprar un SSD 1TB, mi email es al@gmail.com")
        self.assertEqual(res["state"]["tipo_solicitud"], "venta")
        self.assertEqual(res["state"]["estado_ticket"], "venta_procesada")

    def test_tier3_case3(self):
        # Sales out of stock check
        inv = read_inventory()
        inv["SSD_1TB"]["stock"] = 0
        write_inventory(inv)
        status, res = self.simulate("T3C3", "Alejandro Ruiz compra SSD 1TB")
        self.assertFalse(res["state"]["inventario"]["SSD_1TB"]["disponible"])

    def test_tier3_case4(self):
        # Repair stock mediation with checkpointer status query
        self.simulate("T3C4", "Sofía Gómez PC gamer no arranca")
        status, data = self.get_status("T3C4")
        self.assertIn("RAM_16GB", data["state"]["diagnostico"]["repuestos_necesarios"])
        self.assertEqual(data["state"]["next_step"], "reparar_equipo")

    def test_tier3_case5(self):
        # Mediation pricing triggers budget changes and notifications
        status, res = self.simulate("T3C5", "Sofía Gómez PC gamer no arranca")
        total = sum(v["precio"] for v in res["state"]["inventario"].values()) + res["state"]["diagnostico"]["costo_mano_obra"]
        self.assertEqual(total, 220.0)
        notif_events = [e for e in res["events"] if e["evento"] == "cliente.notificado"]
        self.assertTrue(len(notif_events) > 0)
        self.assertIn("$220", notif_events[0]["payload"]["mensaje_cliente"])

    def test_tier3_case6(self):
        # Resume approved triggers quality check and final notifications
        self.simulate("T3C6", "Carlos Pérez HP screen broken")
        status, res = self.resume("T3C6", "approved")
        events = res["events"]
        qc_event = [e for e in events if e["evento"] == "calidad.aprobada"]
        self.assertTrue(len(qc_event) > 0)

    def test_tier3_case7(self):
        # Telemetry tracking during stock mediation and budget generation
        status, res = self.simulate("T3C7", "Sofía Gómez PC gamer no arranca")
        self.assertIsNotNone(res["state"].get("telemetry"))

    def test_tier3_case8(self):
        # Simultaneous multiple paused threads in checkpointer
        self.simulate("T3C8_1", "Carlos Pérez HP screen broken")
        self.simulate("T3C8_2", "Sofía Gómez PC gamer no arranca")
        
        status1, data1 = self.get_status("T3C8_1")
        status2, data2 = self.get_status("T3C8_2")
        
        self.assertEqual(data1["state"]["cliente"]["nombre"], "Carlos Pérez")
        self.assertEqual(data2["state"]["cliente"]["nombre"], "Sofía Gómez")

    def test_tier3_case9(self):
        # Ambiguous support query resolves to Venta
        self.simulate("T3C9", "hola")
        status, res = self.simulate("T3C9", "quiero comprar un SSD 1TB de Alejandro Ruiz")
        self.assertEqual(res["state"]["tipo_solicitud"], "venta")

    # ----------------------------------------------------
    # TIER 4 - Real-World Scenarios (9 cases)
    # ----------------------------------------------------
    def test_tier4_case1(self):
        # Lucia Dell Inspiron E2E Multi-turn Flow
        status, res = self.simulate("T4C1", "Hola soy Lucía y mi compu no anda")
        self.assertEqual(res["state"]["tipo_solicitud"], "ambiguo")
        self.assertEqual(res["state"]["next_step"], "pedir_aclaracion")

        status, res2 = self.simulate("T4C1", "Es una Dell Inspiron que se calienta, mi email es lucia@outlook.com y prefiero email")
        self.assertEqual(res2["state"]["tipo_solicitud"], "reparacion")
        self.assertEqual(res2["state"]["next_step"], "reparar_equipo")

        # Resume approve
        status, res3 = self.resume("T4C1", "approved")
        self.assertEqual(res3["state"]["estado_ticket"], "entregado")
        self.assertIsNone(res3["state"]["next_step"])

    def test_tier4_case2(self):
        # Carlos E2E flow with pause, status verification, and approved resume
        status, res = self.simulate("T4C2", "Carlos Pérez HP screen broken")
        self.assertEqual(res["state"]["next_step"], "reparar_equipo")
        
        # Verify status
        status, data = self.get_status("T4C2")
        self.assertEqual(data["state"]["estado_ticket"], "presupuestado")
        
        # Resume approved
        status, res2 = self.resume("T4C2", "approved")
        self.assertEqual(res2["state"]["estado_ticket"], "entregado")

    def test_tier4_case3(self):
        # Sofia E2E flow with out of stock, mediation, pause, and rejected resume
        status, res = self.simulate("T4C3", "Sofía Gómez PC gamer no arranca")
        self.assertEqual(res["state"]["next_step"], "reparar_equipo")
        self.assertIn("RAM_16GB", res["state"]["diagnostico"]["repuestos_necesarios"])
        
        # Check stock of RAM_16GB is decremented (baseline is 5, so now 4)
        inv = read_inventory()
        self.assertEqual(inv["RAM_16GB"]["stock"], 4)
        
        # Reject
        status, res2 = self.resume("T4C3", "rejected")
        self.assertEqual(res2["state"]["estado_ticket"], "cancelado")
        
        # Check stock of RAM_16GB is released back to 5
        inv2 = read_inventory()
        self.assertEqual(inv2["RAM_16GB"]["stock"], 5)

    def test_tier4_case4(self):
        # Parallel execution of multiple threads with concurrent SQLite checks
        threads = []
        errors = []
        
        def run_thread(t_id, name):
            try:
                status, res = self.simulate(t_id, f"Hola soy {name}, mi HP tiene la pantalla rota.")
                if status != 200 or res["state"]["cliente"]["nombre"] != name:
                    errors.append(f"Thread {t_id} failed")
            except Exception as e:
                errors.append(str(e))
                
        for i in range(5):
            t = threading.Thread(target=run_thread, args=(f"T4C4_{i}", f"Carlos {i}"))
            threads.append(t)
            t.start()
            
        for t in threads:
            t.join()
            
        self.assertEqual(len(errors), 0, f"Errors in parallel test: {errors}")

    def test_tier4_case5(self):
        # GET /api/status for paused vs resumed threads
        self.simulate("T4C5", "Carlos Pérez HP screen broken")
        status, data1 = self.get_status("T4C5")
        self.assertEqual(data1["state"]["next_step"], "reparar_equipo")
        
        self.resume("T4C5", "approved")
        status, data2 = self.get_status("T4C5")
        self.assertIsNone(data2["state"]["next_step"])

    def test_tier4_case6(self):
        # GET /api/stream SSE transitions stream
        self.simulate("T4C6", "Carlos Pérez HP screen broken")
        status, data_str = self.get_stream("T4C6")
        self.assertEqual(status, 200)
        self.assertIn("atencion_cliente", data_str)
        self.assertIn("tecnico_diagnostico", data_str)
        self.assertIn("almacen", data_str)
        self.assertIn("orquestador", data_str)

    def test_tier4_case7(self):
        # SQLite database persistence across checkpointer instances
        cp1 = SQLiteCheckpointer()
        cp1.save("T4C7", {"test": "value"})
        
        cp2 = SQLiteCheckpointer()
        res = cp2.load("T4C7")
        self.assertIsNotNone(res)
        self.assertEqual(res[0]["test"], "value")

    def test_tier4_case8(self):
        # Verify token usage and latency telemetry keys
        self.simulate("T4C8", "Carlos Pérez HP screen broken")
        status, data = self.get_status("T4C8")
        telemetry = data["state"].get("telemetry")
        self.assertIsNotNone(telemetry)
        self.assertIn("atencion_cliente", telemetry["latencies"])
        self.assertIn("atencion_cliente", telemetry["tokens"])

    def test_tier4_case9(self):
        # Recovery of checkpoints database reset
        self.simulate("T4C9", "Carlos Pérez HP screen broken")
        # Reset DB via server call
        url = f"http://127.0.0.1:{self.port}/api/simulate"
        payload = {"reset_stock": True}
        status, data = http_post(url, payload)
        self.assertEqual(status, 200)
        
        # Old checkpoint should be deleted/missing
        url_status = f"http://127.0.0.1:{self.port}/api/status?thread_id=T4C9"
        try:
            http_get(url_status)
            self.fail("Expected 404 for deleted thread")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)

if __name__ == "__main__":
    unittest.main()
