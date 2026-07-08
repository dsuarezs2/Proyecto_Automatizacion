import os
import sys
import unittest

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from tests.utils import reset_inventory
from src.graph import TechServGraph

class TestFlujoVenta(unittest.TestCase):
    def setUp(self):
        reset_inventory()
        self.graph = TechServGraph()

    def test_compra_ssd_disponible(self):
        """
        Caso 3: Compra de SSD 1TB - Disponible en almacén y recomendación con 10% de descuento
        """
        ticket_id = "TKT-TEST-003"
        client_input = "Hola, me llamo Alejandro Ruiz, contacto al@gmail.com, prefiero email. Quiero comprar un SSD 1TB para actualizar mi equipo."
        
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
        self.assertEqual(state["estado_ticket"], "venta_procesada")
        self.assertEqual(state["tipo_solicitud"], "venta")
        
        diagnostico = state["diagnostico"]
        self.assertIn("SSD_1TB", diagnostico["repuestos_necesarios"])
        
        # Base: $110. Discount 10% = $11. Final cost: $99.
        total_cost = sum(v["precio"] for v in state["inventario_status"].values()) + diagnostico["costo_mano_obra"]
        self.assertEqual(total_cost, 99.0)
        
        self.assertTrue(state["inventario_status"]["SSD_1TB"]["disponible"])

if __name__ == "__main__":
    unittest.main()
