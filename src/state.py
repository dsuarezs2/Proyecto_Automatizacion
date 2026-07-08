from typing import List, Dict, Any, Optional
from typing_extensions import TypedDict
from pydantic import BaseModel, Field

class ClienteSchema(BaseModel):
    nombre: str = Field(default="")
    contacto: str = Field(default="")
    canal_preferido: str = Field(default="email")

class EquipoSchema(BaseModel):
    marca_modelo: str = Field(default="")
    descripcion: str = Field(default="")
    sintomas: List[str] = Field(default_factory=list)

class DiagnosticoSchema(BaseModel):
    falla_confirmada: str = Field(default="")
    repuestos_necesarios: List[str] = Field(default_factory=list)
    costo_mano_obra: float = Field(default=0.0)
    tiempo_estimado_horas: int = Field(default=0)

# Estado oficial del Grafo LangGraph
class TechServState(TypedDict):
    ticket_id: str
    thread_id: Optional[str]
    cliente: ClienteSchema
    equipo: EquipoSchema
    tipo_solicitud: str  # "venta", "reparacion", "soporte", "ambiguo"
    diagnostico: DiagnosticoSchema
    inventario_status: Dict[str, Any]
    estado_ticket: str  # "recibido", "presupuestado", "en_reparacion", "entregado", etc.
    historial_conversacion: List[Dict[str, str]]
    next_step: Optional[str]
    telemetry: Optional[Dict[str, Any]]
    token_usage: Optional[Dict[str, int]]   # tokens reales por nodo (de Gemini API)
    mediation_cycles: Optional[int]          # ciclos de mediación de stock
    node_transitions: Optional[List[Dict[str, str]]]  # trazas de transiciones de nodo
    mcp_events: Optional[List[Dict[str, Any]]]  # eventos del bus MCP

