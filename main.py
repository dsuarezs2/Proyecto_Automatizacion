import os
import sys
import time
from datetime import datetime
from tests.utils import reset_inventory
from src.graph import TechServGraph

def run_ticket_simulation(graph: TechServGraph, ticket_id: str, client_input: str, follow_up_input: str = None) -> bool:
    print("\n" + "="*80)
    print(f" PROCESANDO TICKET: {ticket_id}")
    print(f" INPUT CLIENTE: \"{client_input}\"")
    print("="*80 + "\n")
    
    # Initialize state
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
    
    start_time = time.time()
    state, events, success = graph.execute(state, client_input)
    
    # Check if we need follow up
    if not success and state.get("tipo_solicitud") == "ambiguo" and follow_up_input:
        print("\n\033[93m[Simulador] -> Cliente provee aclaración interactiva...\033[0m")
        print(f"\033[93m[Simulador] Aclaración Cliente: \"{follow_up_input}\"\033[0m\n")
        state, follow_up_events, success = graph.execute(state, follow_up_input)
        events.extend(follow_up_events)
        
    elapsed_time_ms = round((time.time() - start_time) * 1000, 2)
    
    # Print the event logs sequentially
    for ev in events:
        timestamp = ev["timestamp"]
        print(f"[{timestamp}] \033[92m{ev['evento']}\033[0m publicado por \033[1m{ev['agente_emisor']}\033[0m")
        print(f"    Payload: {ev['payload']}")
        
    print("\n" + "-"*80)
    print(f" RESULTADO FINAL DEL TICKET {ticket_id}: {'COMPLETADO CON ÉXITO' if success else 'RECHAZADO/PENDIENTE'}")
    print(f" Estado Final en TechServState: {state.get('estado_ticket')}")
    print(f" Latencia: {elapsed_time_ms} ms")
    print("-"*80 + "\n")
    
    return success

def main():
    print("\033[1;92m" + "="*80)
    print(" INICIALIZANDO REMAKE DEL SISTEMA MULTIAGENTE TECHSERV (LANGGRAPH STUB)")
    print("="*80 + "\033[0m")
    
    # Reset stock level at the start of tests
    reset_inventory()
    
    graph = TechServGraph()
    
    tickets = [
        {
            "id": "TKT-2026-001",
            "input": "Hola, me llamo Carlos Pérez, mi cel es +5491133334444 y prefiero whatsapp. Mi laptop HP tiene la pantalla rota.",
            "follow_up": None
        },
        {
            "id": "TKT-2026-002",
            "input": "Buenas, soy Sofía Gómez, mi email es sofia@gmail.com, celular +5491155556666, prefiero sms. Mi PC gamer de escritorio no arranca para nada.",
            "follow_up": None
        },
        {
            "id": "TKT-2026-003",
            "input": "Hola, me llamo Alejandro Ruiz, contacto al@gmail.com, prefiero email. Quiero comprar un SSD 1TB para actualizar mi equipo.",
            "follow_up": None
        },
        {
            "id": "TKT-2026-004",
            "input": "Hola, soy Mateo Torres, celular +5491188887777, prefiero whatsapp. Mi tablet con teclado no responde bluetooth.",
            "follow_up": None
        },
        {
            "id": "TKT-2026-005",
            "input": "Hola, me llamo Lucía y mi compu no anda.",
            "follow_up": "Es una Laptop Dell Inspiron, se calienta demasiado y se apaga a los 10 minutos de uso. Mi contacto es lucia@outlook.com y prefiero email."
        }
    ]
    
    success_count = 0
    start_all = time.time()
    
    for t in tickets:
        success = run_ticket_simulation(graph, t["id"], t["input"], t["follow_up"])
        if success:
            success_count += 1
        time.sleep(0.1)
        
    total_elapsed = round((time.time() - start_all) * 1000, 2)
    
    print("\n" + "="*80)
    print(" REPORTES DE MÉTRICAS GLOBALES DEL SISTEMA (TELEMETRÍA SIMULADA)")
    print("="*80)
    print(f"Tickets Totales Procesados: {len(tickets)}")
    print(f"Tickets Exitosos (Autónomos): {success_count}")
    print(f"Tasa de Éxito: {round((success_count / len(tickets)) * 100, 2)}%")
    print(f"Latencia Total del Sistema: {total_elapsed} ms")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
