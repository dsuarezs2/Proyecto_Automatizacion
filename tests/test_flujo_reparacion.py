import os
import sys
import unittest

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from tests.utils import reset_inventory
from src.graph import TechServGraph

class TestFlujoReparacion(unittest.TestCase):
    def setUp(self):
        reset_inventory()
        self.graph = TechServGraph()

    def test_reparacion_pantalla_disponible(self):
        """
        Caso 1: Laptop HP con pantalla rota - Repuesto disponible en almacén
        """
        ticket_id = "TKT-TEST-001"
        client_input = "Hola, soy Carlos Pérez, mi cel es +5491133334444 y prefiero whatsapp. Mi laptop HP tiene la pantalla rota."
        
        state = {
            "ticket_id": ticket_id,
            "cliente": {
                "nombre": "",
                "contacto": "",
                "canal_preferido": "email"
            },
            "equipo": {
                "marca_modelo": "",
                "descripcion": "",
                "sintomas": []
            },
            "tipo_solicitud": "",
            "diagnostico": {
                "falla_confirmada": "",
                "repuestos_necesarios": [],
                "costo_mano_obra": 0.0,
                "tiempo_estimado_horas": 0
            },
            "inventario_status": {},
            "estado_ticket": "recibido",
            "historial_conversacion": [],
            "next_step": None
        }

        state, events, success = self.graph.execute(state, client_input)

        self.assertTrue(success)
        self.assertEqual(state["estado_ticket"], "entregado")
        self.assertEqual(state["tipo_solicitud"], "reparacion")
        
        cliente = state["cliente"]
        self.assertEqual(cliente["nombre"], "Carlos Pérez")
        self.assertEqual(cliente["canal_preferido"], "whatsapp")
        
        equipo = state["equipo"]
        self.assertIn("HP", equipo["marca_modelo"])
        
        diagnostico = state["diagnostico"]
        self.assertIn("Pantalla_HP", diagnostico["repuestos_necesarios"])
        
        total_cost = state["inventario_status"]["Pantalla_HP"]["precio"] + diagnostico["costo_mano_obra"]
        self.assertEqual(total_cost, 170.0)

    def test_reparacion_ram_agotada_mediacion(self):
        """
        Caso 2: PC gamer sin arranque - RAM de 8GB agotada - Mediación a RAM 16GB
        """
        ticket_id = "TKT-TEST-002"
        client_input = "Buenas, soy Sofía Gómez, mi email es sofia@gmail.com, celular +5491155556666, prefiero sms. Mi PC gamer de escritorio no arranca para nada."
        
        state = {
            "ticket_id": ticket_id,
            "cliente": {
                "nombre": "",
                "contacto": "",
                "canal_preferido": "email"
            },
            "equipo": {
                "marca_modelo": "",
                "descripcion": "",
                "sintomas": []
            },
            "tipo_solicitud": "",
            "diagnostico": {
                "falla_confirmada": "",
                "repuestos_necesarios": [],
                "costo_mano_obra": 0.0,
                "tiempo_estimado_horas": 0
            },
            "inventario_status": {},
            "estado_ticket": "recibido",
            "historial_conversacion": [],
            "next_step": None
        }

        state, events, success = self.graph.execute(state, client_input)

        self.assertTrue(success)
        self.assertEqual(state["estado_ticket"], "entregado")
        
        diagnostico = state["diagnostico"]
        self.assertIn("Fuente_Poder", diagnostico["repuestos_necesarios"])
        self.assertIn("RAM_16GB", diagnostico["repuestos_necesarios"])
        self.assertNotIn("RAM_8GB", diagnostico["repuestos_necesarios"])
        
        total_cost = sum(v["precio"] for v in state["inventario_status"].values()) + diagnostico["costo_mano_obra"]
        self.assertEqual(total_cost, 220.0)

if __name__ == "__main__":
    unittest.main()
