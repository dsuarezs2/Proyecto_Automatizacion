import os
import json
import unittest
import tempfile
from unittest.mock import MagicMock
from langchain_core.documents import Document
from src.agents.tools import create_technical_tools

class MockVectorStore:
    def __init__(self):
        self.docs = [
            Document(page_content="HP Screen Replacement manual. Part: PART-SCREEN-HP.", metadata={"source": "display.md"}),
            Document(page_content="Boot failure. Needs PSU (PART-PSU-600) and RAM (PART-RAM-DDR4-8G). Alternate: PART-RAM-DDR4-16G.", metadata={"source": "boot.md"}),
            Document(page_content="Overheating issues. Requires Pasta_Termica (PART-THERMAL-PASTE) and Ventilador_CPU (PART-FAN-CPU).", metadata={"source": "cooling.md"})
        ]

    def similarity_search_with_score(self, query, k=3):
        return [(doc, 0.1) for doc in self.docs[:k]]

    def similarity_search(self, query, k=3):
        return self.docs[:k]

class TestReActTools(unittest.TestCase):
    def setUp(self):
        # Create a mock inventory database
        self.inventory_data = {
            "Pantalla_HP": {
                "price": 120.0,
                "stock": 5
            },
            "RAM_8GB": {
                "price": 45.0,
                "stock": 0
            },
            "RAM_16GB": {
                "price": 80.0,
                "stock": 10
            },
            "Fuente_Poder": {
                "price": 90.0,
                "stock": 2
            },
            "Pasta_Termica": {
                "price": 15.0,
                "stock": 20
            },
            "Ventilador_CPU": {
                "price": 20.0,
                "stock": 15
            }
        }
        self.temp_dir = tempfile.TemporaryDirectory()
        self.inventory_db_path = os.path.join(self.temp_dir.name, "inventario.json")
        with open(self.inventory_db_path, "w", encoding="utf-8") as f:
            json.dump(self.inventory_data, f, indent=2)
            
        self.vector_store = MockVectorStore()
        # Create the tools using the factory function
        self.tools = create_technical_tools(self.vector_store, self.inventory_db_path)
        self.query_manuals_tool = self.tools[0]
        self.get_parts_list_tool = self.tools[1]
        self.calculate_labor_tool = self.tools[2]
        self.suggest_alternatives_tool = self.tools[3]

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_query_manuals(self):
        """Test query_manuals tool searches the vector store and returns JSON results."""
        res_json = self.query_manuals_tool.invoke({"query": "screen replacement", "top_k": 1})
        res = json.loads(res_json)
        self.assertIn("results", res)
        self.assertEqual(len(res["results"]), 1)
        self.assertIn("HP Screen Replacement", res["results"][0]["content"])
        self.assertEqual(res["results"][0]["metadata"]["source"], "display.md")

    def test_get_parts_list_hp_screen(self):
        """Test get_parts_list tool returns the correct HP Screen replacement parts."""
        res_json = self.get_parts_list_tool.invoke({"brand_model": "HP Laptop", "symptoms": ["pantalla rota", "vidrio quebrado"]})
        res = json.loads(res_json)
        self.assertIn("piezas_requeridas", res)
        self.assertEqual(len(res["piezas_requeridas"]), 1)
        self.assertEqual(res["piezas_requeridas"][0]["nombre"], "Pantalla_HP")
        self.assertEqual(res["piezas_requeridas"][0]["precio_unitario"], 120.0)

    def test_get_parts_list_boot_failure(self):
        """Test get_parts_list tool returns the correct boot failure parts."""
        res_json = self.get_parts_list_tool.invoke({"brand_model": "PC Gamer", "symptoms": ["no enciende", "sin energia"]})
        res = json.loads(res_json)
        self.assertIn("piezas_requeridas", res)
        parts = {p["nombre"]: p for p in res["piezas_requeridas"]}
        self.assertIn("Fuente_Poder", parts)
        self.assertIn("RAM_8GB", parts)
        self.assertEqual(parts["Fuente_Poder"]["precio_unitario"], 90.0)
        self.assertEqual(parts["RAM_8GB"]["precio_unitario"], 45.0)

    def test_get_parts_list_overheating(self):
        """Test get_parts_list tool returns the correct overheating parts."""
        res_json = self.get_parts_list_tool.invoke({"brand_model": "Dell Laptop", "symptoms": ["se sobrecalienta", "calienta demasiado"]})
        res = json.loads(res_json)
        self.assertIn("piezas_requeridas", res)
        parts = {p["nombre"]: p for p in res["piezas_requeridas"]}
        self.assertIn("Pasta_Termica", parts)
        self.assertIn("Ventilador_CPU", parts)
        self.assertEqual(parts["Pasta_Termica"]["precio_unitario"], 15.0)
        self.assertEqual(parts["Ventilador_CPU"]["precio_unitario"], 20.0)

    def test_calculate_labor_standard(self):
        """Test calculate_labor tool with standard inputs."""
        res_json = self.calculate_labor_tool.invoke({"repair_type": "pantalla_reemplazo", "complexity": "medium"})
        res = json.loads(res_json)
        self.assertEqual(res["costo_mano_obra"], 50.0)
        self.assertEqual(res["tiempo_estimado_horas"], 2)

        res_json = self.calculate_labor_tool.invoke({"repair_type": "sobrecalentamiento", "complexity": "medium"})
        res = json.loads(res_json)
        self.assertEqual(res["costo_mano_obra"], 40.0)
        self.assertEqual(res["tiempo_estimado_horas"], 1)

    def test_calculate_labor_complexity(self):
        """Test calculate_labor tool adjusts correctly for complexity."""
        res_json = self.calculate_labor_tool.invoke({"repair_type": "pantalla_reemplazo", "complexity": "simple"})
        res = json.loads(res_json)
        self.assertEqual(res["costo_mano_obra"], 40.0)
        self.assertEqual(res["tiempo_estimado_horas"], 1)

        res_json = self.calculate_labor_tool.invoke({"repair_type": "pantalla_reemplazo", "complexity": "complex"})
        res = json.loads(res_json)
        self.assertEqual(res["costo_mano_obra"], 60.0)
        self.assertEqual(res["tiempo_estimado_horas"], 3)

    def test_suggest_alternatives_ram(self):
        """Test suggest_alternatives tool for out-of-stock RAM."""
        res_json = self.suggest_alternatives_tool.invoke({
            "missing_part_code": "PART-RAM-DDR4-8G",
            "missing_part_name": "Memoria RAM DDR4 8GB",
            "brand_model": "PC Gamer"
        })
        res = json.loads(res_json)
        self.assertIn("alternatives", res)
        self.assertEqual(len(res["alternatives"]), 1)
        self.assertEqual(res["alternatives"][0]["nombre"], "RAM_16GB")
        self.assertEqual(res["alternatives"][0]["precio_unitario"], 80.0)

    def test_handle_alternative_key_layout(self):
        """Test tools handle inventory with different layouts (where keys are names or codes)."""
        alt_inventory_data = {
            "PART-SCREEN-HP": {
                "nombre": "Pantalla HP Laptop 15",
                "price": 120.0,
                "stock": 5
            },
            "PART-RAM-DDR4-8G": {
                "nombre": "Memoria RAM DDR4 8GB",
                "price": 45.0,
                "stock": 0
            },
            "PART-RAM-DDR4-16G": {
                "nombre": "Memoria RAM DDR4 16GB",
                "price": 80.0,
                "stock": 10
            }
        }
        with open(self.inventory_db_path, "w", encoding="utf-8") as f:
            json.dump(alt_inventory_data, f, indent=2)
            
        tools = create_technical_tools(self.vector_store, self.inventory_db_path)
        get_parts = tools[1]
        suggest_alt = tools[3]
        
        res_json = get_parts.invoke({"brand_model": "HP Laptop", "symptoms": ["pantalla rota"]})
        res = json.loads(res_json)
        self.assertEqual(len(res["piezas_requeridas"]), 1)
        self.assertEqual(res["piezas_requeridas"][0]["nombre"], "PART-SCREEN-HP")
        
        res_json = suggest_alt.invoke({
            "missing_part_code": "PART-RAM-DDR4-8G",
            "missing_part_name": "Memoria RAM DDR4 8GB",
            "brand_model": "PC Gamer"
        })
        res = json.loads(res_json)
        self.assertEqual(len(res["alternatives"]), 1)
        self.assertEqual(res["alternatives"][0]["nombre"], "PART-RAM-DDR4-16G")

if __name__ == "__main__":
    unittest.main()
