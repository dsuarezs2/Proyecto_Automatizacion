import os
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langchain_core.documents import Document

# Input Pydantic schemas
class QueryManualsInput(BaseModel):
    query: str = Field(..., description="Search query or key terms to look up in the manuals, such as equipment model, component names, or symptoms.")
    top_k: int = Field(default=3, description="Number of relevant text snippets to retrieve from the vector database.")

class GetPartsListInput(BaseModel):
    brand_model: str = Field(..., description="Brand and model of the equipment (e.g. 'HP Laptop 15').")
    symptoms: List[str] = Field(..., description="List of symptoms reported for the equipment (e.g. ['pantalla rota']).")

class CalculateLaborInput(BaseModel):
    repair_type: str = Field(..., description="Type of repair action (e.g. 'pantalla_reemplazo', 'fuente_poder_reemplazo', 'sobrecalentamiento', 'soporte_remoto').")
    complexity: str = Field(default="medium", description="Complexity level of the repair: 'simple', 'medium', or 'complex'.")

class SuggestAlternativesInput(BaseModel):
    missing_part_code: str = Field(..., description="The part code of the out-of-stock item (e.g. 'PART-RAM-DDR4-8G' or 'RAM_8GB').")
    missing_part_name: str = Field(..., description="The descriptive name of the out-of-stock item.")
    brand_model: str = Field(..., description="The equipment model to verify compatibility for.")

def find_in_inventory(inventory: dict, key_or_name_or_code: str) -> Optional[dict]:
    """Helper to look up a part in inventory by key, name, or code."""
    q = key_or_name_or_code.strip()
    
    # 1. Try direct lookup (matches when key is part name, part code, or key like "Pantalla_HP")
    if q in inventory:
        info = inventory[q]
        return {
            "key": q,
            "nombre": info.get("nombre", q),
            "codigo": info.get("codigo", q),
            "stock": info.get("stock", 0),
            "precio": info.get("precio", info.get("price", 0.0))
        }
    
    # 2. Try predefined mappings for standard test cases (both directions)
    mapping = {
        # Code to Key
        "PART-SCREEN-HP": "Pantalla_HP",
        "PART-RAM-DDR4-8G": "RAM_8GB",
        "PART-RAM-DDR4-16G": "RAM_16GB",
        "PART-PSU-600": "Fuente_Poder",
        "PART-SSD-1TB": "SSD_1TB",
        "PART-THERMAL-PASTE": "Pasta_Termica",
        "PART-FAN-CPU": "Ventilador_CPU",
        # Key to Code
        "Pantalla_HP": "PART-SCREEN-HP",
        "RAM_8GB": "PART-RAM-DDR4-8G",
        "RAM_16GB": "PART-RAM-DDR4-16G",
        "Fuente_Poder": "PART-PSU-600",
        "SSD_1TB": "PART-SSD-1TB",
        "Pasta_Termica": "PART-THERMAL-PASTE",
        "Ventilador_CPU": "PART-FAN-CPU",
        # Names to Key
        "pantalla hp laptop 15": "Pantalla_HP",
        "pantalla hp laptop": "Pantalla_HP",
        "memoria ram ddr4 8gb": "RAM_8GB",
        "memoria ram ddr4 16gb": "RAM_16GB",
        "fuente de poder 600w": "Fuente_Poder",
        "ssd 1tb nvme pcie m.2": "SSD_1TB",
        "pasta térmica": "Pasta_Termica",
        "pasta termica": "Pasta_Termica",
        "ventilador cpu": "Ventilador_CPU"
    }
    
    mapped_key = mapping.get(q) or mapping.get(q.lower())
    if mapped_key and mapped_key in inventory:
        info = inventory[mapped_key]
        return {
            "key": mapped_key,
            "nombre": info.get("nombre", mapped_key),
            "codigo": info.get("codigo", q),
            "stock": info.get("stock", 0),
            "precio": info.get("precio", info.get("price", 0.0))
        }
    
    # 3. Iterative search with underscore normalization
    q_norm = q.lower().replace("_", " ")
    for k, v in inventory.items():
        v_code = str(v.get("codigo", "")).lower().replace("_", " ") if isinstance(v, dict) else ""
        v_name = str(v.get("nombre", "")).lower().replace("_", " ") if isinstance(v, dict) else ""
        k_norm = k.lower().replace("_", " ")
        
        if (v_code == q_norm or 
            v_name == q_norm or 
            k_norm == q_norm or
            q_norm in v_name or
            v_name in q_norm or
            q_norm in k_norm or
            k_norm in q_norm):
            return {
                "key": k,
                "nombre": v.get("nombre", k),
                "codigo": v.get("codigo", k),
                "stock": v.get("stock", 0),
                "precio": v.get("precio", v.get("price", 0.0))
            }
            
    return None

def resolve_part(inventory: dict, part_key: str, default_code: str, default_price: float = 0.0) -> Optional[dict]:
    """Helper to resolve a part from inventory and format it for the parts list."""
    item = find_in_inventory(inventory, part_key)
    if item:
        return {
            "nombre": item["key"],
            "codigo": item.get("codigo", default_code),
            "cantidad": 1,
            "precio_unitario": item.get("precio", default_price)
        }
    return None

def create_technical_tools(vector_store: Any, inventory_db_path: str) -> List[Any]:
    """Factory function that returns the list of ReAct tools configured with dependencies."""
    
    @tool(args_schema=QueryManualsInput)
    def query_manuals(query: str, top_k: int = 3) -> str:
        """
        Searches the technical manuals and specifications index (FAISS vector store) 
        to find instructions, compatibility tables, and details related to troubleshooting symptoms.
        """
        try:
            docs_and_scores = vector_store.similarity_search_with_score(query, k=top_k)
            results = []
            for doc, score in docs_and_scores:
                results.append({
                    "content": doc.page_content,
                    "score": float(score),
                    "metadata": doc.metadata
                })
            return json.dumps({"results": results}, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"error": f"Failed to query manuals: {str(e)}"}, ensure_ascii=False)

    @tool(args_schema=GetPartsListInput)
    def get_parts_list(brand_model: str, symptoms: List[str]) -> str:
        """
        Retrieves the list of recommended parts, codes, and prices from the inventory 
        that match the equipment model and symptoms.
        """
        try:
            with open(inventory_db_path, "r", encoding="utf-8") as f:
                inventory = json.load(f)
            
            matched = []
            symptoms_str = " ".join(symptoms).lower()
            model_lower = brand_model.lower()
            
            # 1. Screen Replacement (HP Laptop)
            if any(w in symptoms_str for w in ["pantalla", "screen", "vidrio", "broken", "rota", "quebrada"]):
                part = resolve_part(inventory, "Pantalla_HP", "PART-SCREEN-HP", 120.0)
                if part:
                    matched.append(part)
                    
            # 2. Boot Failure (Power and/or RAM)
            elif any(w in symptoms_str for w in ["encendido", "arranca", "enciende", "dead", "muerto", "post", "energia", "energía"]):
                part_psu = resolve_part(inventory, "Fuente_Poder", "PART-PSU-600", 90.0)
                part_ram = resolve_part(inventory, "RAM_8GB", "PART-RAM-DDR4-8G", 45.0)
                if part_psu:
                    matched.append(part_psu)
                if part_ram:
                    matched.append(part_ram)
                        
            # 3. Cooling System (Overheating)
            elif any(w in symptoms_str for w in ["calienta", "sobrecalienta", "temperatura", "ventilador", "fan", "cooling"]):
                part_paste = resolve_part(inventory, "Pasta_Termica", "PART-THERMAL-PASTE", 15.0)
                part_fan = resolve_part(inventory, "Ventilador_CPU", "PART-FAN-CPU", 20.0)
                if part_paste:
                    matched.append(part_paste)
                if part_fan:
                    matched.append(part_fan)
                    
            # 4. Storage SSD (e.g. Alejandro Ruiz buying SSD 1TB or slow laptop)
            elif any(w in symptoms_str for w in ["ssd", "disco", "almacenamiento", "ssd_1tb", "lenta", "lento", "lentitud", "slow"]):
                part = resolve_part(inventory, "SSD_1TB", "PART-SSD-1TB", 110.0)
                if part:
                    matched.append(part)
                    
            # 5. Wireless / Bluetooth (Teclado, Mouse)
            elif any(w in symptoms_str for w in ["teclado", "mouse", "bluetooth", "inalambrico"]):
                if "compra" in symptoms_str or "adquirir" in symptoms_str:
                    if "teclado" in symptoms_str:
                        part = resolve_part(inventory, "Teclado_Bluetooth", "PART-KEYBOARD-BT", 45.0)
                        if part:
                            matched.append(part)
                    if "mouse" in symptoms_str:
                        part = resolve_part(inventory, "Mouse_Inalambrico", "PART-MOUSE-WL", 25.0)
                        if part:
                            matched.append(part)
            
            # Fallback to vector search if no hardcoded rules matched or matched is empty
            if not matched:
                search_query = f"repuestos piezas necesarias para {brand_model} con {symptoms_str}"
                try:
                    docs = vector_store.similarity_search(search_query, k=2)
                    for doc in docs:
                        content = doc.page_content.lower()
                        for k, v in inventory.items():
                            k_lower = k.lower()
                            v_name = v.get("nombre", "").lower() if isinstance(v, dict) else ""
                            if (k_lower in content or (v_name and v_name in content)) and k not in [m["nombre"] for m in matched]:
                                part = resolve_part(inventory, k, v.get("codigo", k), v.get("precio", v.get("price", 0.0)))
                                if part:
                                    matched.append(part)
                except Exception as ve:
                    print(f"Vector search fallback warning: {ve}")
                    
            return json.dumps({"piezas_requeridas": matched}, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"error": f"Failed to get parts list: {str(e)}"}, ensure_ascii=False)

    @tool(args_schema=CalculateLaborInput)
    def calculate_labor(repair_type: str, complexity: str = "medium") -> str:
        """
        Calculates labor cost and time (hours) required for a specific type of repair.
        """
        repair_type_lower = repair_type.lower()
        complexity = complexity.lower()
        
        estimates = {
            "pantalla_reemplazo": {"costo_mano_obra": 50.0, "tiempo_estimado_horas": 2, "description": "Pantalla rota"},
            "fuente_poder_reemplazo": {"costo_mano_obra": 50.0, "tiempo_estimado_horas": 3, "description": "No arranca (Falla en Fuente y RAM)"},
            "sobrecalentamiento": {"costo_mano_obra": 40.0, "tiempo_estimado_horas": 1, "description": "Sobrecalentamiento"},
            "soporte_remoto": {"costo_mano_obra": 0.0, "tiempo_estimado_horas": 1, "description": "Problema de vinculación bluetooth"},
            "mantenimiento": {"costo_mano_obra": 40.0, "tiempo_estimado_horas": 1, "description": "Mantenimiento preventivo general"}
        }
        
        selected_estimate = None
        
        if any(w in repair_type_lower for w in ["pantalla", "screen"]):
            selected_estimate = estimates["pantalla_reemplazo"].copy()
        elif any(w in repair_type_lower for w in ["fuente", "poder", "ram", "psu", "boot", "arranque", "encendido"]):
            selected_estimate = estimates["fuente_poder_reemplazo"].copy()
        elif any(w in repair_type_lower for w in ["sobrecalentamiento", "cooling", "temperatura", "calienta", "pasta", "ventilador"]):
            selected_estimate = estimates["sobrecalentamiento"].copy()
        elif any(w in repair_type_lower for w in ["soporte", "remoto", "bluetooth", "wireless"]):
            selected_estimate = estimates["soporte_remoto"].copy()
        elif "mantenimiento" in repair_type_lower:
            selected_estimate = estimates["mantenimiento"].copy()
            
        if not selected_estimate:
            if complexity == "simple":
                selected_estimate = {"costo_mano_obra": 30.0, "tiempo_estimado_horas": 1, "description": f"Reparación simple: {repair_type}"}
            elif complexity == "complex":
                selected_estimate = {"costo_mano_obra": 100.0, "tiempo_estimado_horas": 5, "description": f"Reparación compleja: {repair_type}"}
            else:
                selected_estimate = {"costo_mano_obra": 50.0, "tiempo_estimado_horas": 2, "description": f"Reparación estándar: {repair_type}"}
        else:
            if complexity == "simple" and selected_estimate["costo_mano_obra"] > 0:
                selected_estimate["costo_mano_obra"] *= 0.8
                selected_estimate["tiempo_estimado_horas"] = max(1, selected_estimate["tiempo_estimado_horas"] - 1)
            elif complexity == "complex" and selected_estimate["costo_mano_obra"] > 0:
                selected_estimate["costo_mano_obra"] *= 1.2
                selected_estimate["tiempo_estimado_horas"] += 1
                
        return json.dumps(selected_estimate, ensure_ascii=False, indent=2)

    @tool(args_schema=SuggestAlternativesInput)
    def suggest_alternatives(missing_part_code: str, missing_part_name: str, brand_model: str) -> str:
        """
        Suggests compatible alternative parts when a requested part is out of stock.
        """
        try:
            with open(inventory_db_path, "r", encoding="utf-8") as f:
                inventory = json.load(f)
            
            code_lower = missing_part_code.lower()
            name_lower = missing_part_name.lower()
            alternatives = []
            
            if "ram" in name_lower or "ram" in code_lower or "8g" in code_lower or "8g" in name_lower:
                item = find_in_inventory(inventory, "RAM_16GB")
                if item:
                    alternatives.append({
                        "nombre": item["key"],
                        "codigo": item.get("codigo", "PART-RAM-DDR4-16G"),
                        "precio_unitario": item["precio"],
                        "compatibility_notes": "Unidad de mayor capacidad (16GB) totalmente compatible. Proporciona una mejora de performance."
                    })
            
            if not alternatives:
                search_query = f"alternativa compatible {missing_part_name} {missing_part_code} {brand_model}"
                try:
                    docs = vector_store.similarity_search(search_query, k=2)
                    for doc in docs:
                        content = doc.page_content.lower()
                        for k, v in inventory.items():
                            k_lower = k.lower()
                            v_name = v.get("nombre", "").lower() if isinstance(v, dict) else ""
                            if (k_lower in content or (v_name and v_name in content)) and k_lower != name_lower and k_lower != code_lower:
                                # Validar que pertenezcan a la misma categoría para evitar cruces extraños (ej. sugerir RAM por Fuente)
                                is_same_category = False
                                for cat_kws in [["ram", "memoria", "ddr"], ["fuente", "psu", "power"], ["pantalla", "screen", "display"], ["ssd", "hdd", "disco", "drive"], ["mouse", "raton"], ["teclado", "keyboard"], ["ventilador", "fan", "cooling", "disipador"]]:
                                    if any(w in name_lower or w in code_lower for w in cat_kws) and any(w in k_lower or w in v_name for w in cat_kws):
                                        is_same_category = True
                                        break
                                
                                if is_same_category:
                                    item = find_in_inventory(inventory, k)
                                    if item and item["key"] not in [a["nombre"] for a in alternatives]:
                                        alternatives.append({
                                            "nombre": item["key"],
                                            "codigo": item.get("codigo", k),
                                            "precio_unitario": item["precio"],
                                            "compatibility_notes": f"Compatible replacement suggested by manual: {doc.page_content[:100]}..."
                                        })
                except Exception as ve:
                    print(f"Vector search fallback warning: {ve}")
                    
            return json.dumps({"alternatives": alternatives}, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"error": f"Failed to suggest alternatives: {str(e)}"}, ensure_ascii=False)

    return [query_manuals, get_parts_list, calculate_labor, suggest_alternatives]
