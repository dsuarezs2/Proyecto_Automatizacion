import os
import sys
import unittest

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from tests.utils import reset_inventory
from src.graph import TechServGraph

class TestEdgeCases(unittest.TestCase):
    def setUp(self):
        reset_inventory()
        self.graph = TechServGraph()

    def test_soporte_remoto_exitoso(self):
        """
        Caso 4: Tablet con teclado que no responde bluetooth - Soporte remoto resuelve
        """
        ticket_id = "TKT-TEST-004"
        client_input = "Hola, soy Mateo Torres, celular +5491188887777, prefiero whatsapp. Mi tablet con teclado no responde bluetooth."
        
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
        self.assertEqual(state["estado_ticket"], "resuelto_remoto")
        self.assertEqual(state["tipo_solicitud"], "soporte")
        
        diagnostico = state["diagnostico"]
        self.assertEqual(len(diagnostico["repuestos_necesarios"]), 0)
        self.assertEqual(diagnostico["costo_mano_obra"], 0.0)

    def test_input_ambiguo_aclaracion_interactiva(self):
        """
        Caso 5: Input ambiguo 'mi compu no anda'.
        Paso 1: Agente Atención solicita aclaración.
        Paso 2: Cliente responde aclarando y se ejecuta flujo de Reparación por Sobrecalentamiento.
        """
        ticket_id = "TKT-TEST-005"
        first_input = "Hola, me llamo Lucía y mi compu no anda."
        clarification_input = "Es una Laptop Dell Inspiron, se calienta demasiado y se apaga a los 10 minutos de uso. Mi contacto es lucia@outlook.com y prefiero email."

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

        # Step 1: Process ambiguous request
        state, events_first, success_first = self.graph.execute(state, first_input)

        self.assertFalse(success_first)
        self.assertEqual(state["estado_ticket"], "recibido")
        self.assertEqual(state["tipo_solicitud"], "ambiguo")
        
        historial = state["historial_conversacion"]
        self.assertTrue(any("por favor confírmanos" in item["content"] for item in historial))

        # Step 2: Client provides clarification input
        state, events_second, success_second = self.graph.execute(state, clarification_input)

        self.assertTrue(success_second)
        self.assertEqual(state["estado_ticket"], "entregado")
        self.assertEqual(state["tipo_solicitud"], "reparacion")
        
        cliente = state["cliente"]
        self.assertEqual(cliente["nombre"], "Lucía")
        self.assertEqual(cliente["canal_preferido"], "email")
        
        diagnostico = state["diagnostico"]
        self.assertIn("Pasta_Termica", diagnostico["repuestos_necesarios"])
        self.assertIn("Ventilador_CPU", diagnostico["repuestos_necesarios"])
        
        total_cost = sum(v["precio"] for v in state["inventario_status"].values()) + diagnostico["costo_mano_obra"]
        self.assertEqual(total_cost, 75.0)

if __name__ == "__main__":
    unittest.main()
