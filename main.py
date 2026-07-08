import os
import sys
import json
import time
from datetime import datetime
from dotenv import load_dotenv  # carga .env con LANGSMITH_API_KEY etc.

# Cargar variables de entorno (LangSmith, Gemini, etc.)
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(env_path):
    try:
        load_dotenv(env_path)
    except Exception:
        pass

from tests.utils import reset_inventory
from src.graph import TechServGraph


def run_ticket_simulation(
    graph: TechServGraph,
    ticket_id: str,
    client_input: str,
    follow_up_input: str = None,
) -> bool:
    print("\n" + "=" * 80)
    print(f" PROCESANDO TICKET: {ticket_id}")
    print(f" INPUT CLIENTE: \"{client_input}\"")
    print("=" * 80 + "\n")

    state = {
        "ticket_id": ticket_id,
        "thread_id": ticket_id,
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

    start_time = time.time()
    state, events, success = graph.execute(state, client_input)

    # Caso 5: aclaración multiturno
    if not success and state.get("tipo_solicitud") == "ambiguo" and follow_up_input:
        print("\n\033[93m[Simulador] -> Cliente provee aclaración interactiva...\033[0m")
        print(f"\033[93m[Simulador] Aclaración Cliente: \"{follow_up_input}\"\033[0m\n")
        state, follow_up_events, success = graph.execute(state, follow_up_input, resume_decision="approved")
        # Combinar solo los eventos nuevos (no duplicar)
        seen = {json.dumps(e, sort_keys=True) for e in events}
        for ev in follow_up_events:
            key = json.dumps(ev, sort_keys=True)
            if key not in seen:
                events.append(ev)
                seen.add(key)

    elapsed_ms = round((time.time() - start_time) * 1000, 2)

    # Imprimir log de eventos MCP
    for ev in events:
        ts = ev.get("timestamp", "")
        print(f"[{ts}] \033[92m{ev['evento']}\033[0m publicado por \033[1m{ev['agente_emisor']}\033[0m")
        print(f"    Payload: {ev['payload']}")

    # Telemetría por nodo
    telemetry = state.get("telemetry", {})
    token_usage = state.get("token_usage", {})
    if telemetry.get("latencies"):
        print("\n\033[96m[Telemetría de Nodos]\033[0m")
        print(f"  {'Nodo':<25} {'Latencia (ms)':>14} {'Tokens':>8}")
        print(f"  {'-'*25} {'-'*14} {'-'*8}")
        for node, lat in telemetry["latencies"].items():
            tok = token_usage.get(node, telemetry.get("tokens", {}).get(node, "-"))
            print(f"  {node:<25} {lat:>14.2f} {tok:>8}")
        med_cycles = state.get("mediation_cycles", 0)
        if med_cycles:
            print(f"\n  \033[93m⚠ Ciclos de mediación de stock: {med_cycles}\033[0m")

    print("\n" + "-" * 80)
    print(f" RESULTADO FINAL DEL TICKET {ticket_id}: "
          f"{'COMPLETADO CON ÉXITO' if success else 'RECHAZADO/PENDIENTE'}")
    print(f" Estado Final en TechServState: {state.get('estado_ticket')}")
    print(f" Latencia Total: {elapsed_ms} ms")
    print("-" * 80 + "\n")

    return success


def main():
    print("\033[1;92m" + "=" * 80)
    print(" INICIALIZANDO SISTEMA MULTIAGENTE TECHSERV (LANGGRAPH + LANGSMITH)")
    print("=" * 80 + "\033[0m")

    # Mostrar estado de LangSmith
    ls_key = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")
    ls_project = os.getenv("LANGSMITH_PROJECT", "TechServ-LangGraph")
    if ls_key:
        print(f"\033[92m✔ LangSmith activo — Proyecto: {ls_project}\033[0m")
    else:
        print("\033[93m⚠ LangSmith no configurado (LANGSMITH_API_KEY no encontrada)\033[0m")

    reset_inventory()
    graph = TechServGraph()

    tickets = [
        {
            "id": "TKT-2026-001",
            "input": "Hola, me llamo Carlos Pérez, mi cel es +5491133334444 y prefiero whatsapp. Mi laptop HP tiene la pantalla rota.",
            "follow_up": None,
        },
        {
            "id": "TKT-2026-002",
            "input": "Buenas, soy Sofía Gómez, mi email es sofia@gmail.com, celular +5491155556666, prefiero sms. Mi PC gamer de escritorio no arranca para nada.",
            "follow_up": None,
        },
        {
            "id": "TKT-2026-003",
            "input": "Hola, me llamo Alejandro Ruiz, contacto al@gmail.com, prefiero email. Quiero comprar un SSD 1TB para actualizar mi equipo.",
            "follow_up": None,
        },
        {
            "id": "TKT-2026-004",
            "input": "Hola, soy Mateo Torres, celular +5491188887777, prefiero whatsapp. Mi tablet con teclado no responde bluetooth.",
            "follow_up": None,
        },
        {
            "id": "TKT-2026-005",
            "input": "Hola, me llamo Lucía y mi compu no anda.",
            "follow_up": "Es una Laptop Dell Inspiron, se calienta demasiado y se apaga a los 10 minutos de uso. Mi contacto es lucia@outlook.com y prefiero email.",
        },
    ]

    success_count = 0
    start_all = time.time()

    for t in tickets:
        ok = run_ticket_simulation(graph, t["id"], t["input"], t["follow_up"])
        if ok:
            success_count += 1
        time.sleep(0.1)

    total_ms = round((time.time() - start_all) * 1000, 2)

    print("\n" + "=" * 80)
    print(" REPORTES DE MÉTRICAS GLOBALES DEL SISTEMA")
    print("=" * 80)
    print(f"Tickets Totales Procesados : {len(tickets)}")
    print(f"Tickets Exitosos (Autónomos): {success_count}")
    print(f"Tasa de Éxito              : {round((success_count / len(tickets)) * 100, 2)}%")
    print(f"Latencia Total del Sistema : {total_ms} ms")
    if ls_key:
        print(f"\n\033[92m✔ Traces disponibles en https://smith.langchain.com — proyecto '{ls_project}'\033[0m")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
