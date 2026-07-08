/**
 * TechServ - Multi-Agent Swarm Dashboard Controller
 * Handles step-by-step event playback, interactive slot-filling,
 * real-time inventory updates, and responsive telemetry visualization.
 */

// API Configuration
const API_BASE = window.location.origin; // Automatically works with the local server
let activeTicketId = null;
let currentSessionHistory = [];
let isSimulating = false;

// Predefined Demo Cases
const DEMO_CASES = {
    "1": "Hola, soy Juan Pérez. Mi laptop HP Pavilion 15 no da imagen, la pantalla está completamente rota tras golpearse. Mi celular es +54 9 11 5555-0192 y prefiero avisos por whatsapp.",
    "2": "Hola, mi pc gamer no arranca. Al encender hace pitidos y se apaga de golpe. Creo que falla la memoria RAM DDR4 y la fuente de alimentación de 600W. Me llamo Roberto Gómez, mi email es roberto@gmail.com, notificarme por email por favor.",
    "3": "Hola, quisiera comprar un disco SSD de 1TB de alta velocidad para repotenciar mi computadora. ¿Tienen stock disponible y a qué precio? Mi celular es 555-9876, notifíquenme por SMS.",
    "4": "Buenas, compré un teclado bluetooth para mi tablet Lenovo y no responde ni se vincula de ninguna manera. ¿Me pueden ayudar? Mi contacto es 555-4321 y uso SMS.",
    "5": "hola mi compu no anda ayuda"
};

// Document Elements
document.addEventListener("DOMContentLoaded", () => {
    // Initialize Dashboard
    initTabs();
    initDemoButtons();
    initForms();
    refreshInventory();
    refreshTicketHistory();
    
    // Hook refresh history button
    const btnRefreshHistory = document.getElementById("btn-refresh-history");
    if (btnRefreshHistory) {
        btnRefreshHistory.addEventListener("click", refreshTicketHistory);
    }
    
    // Auto-resize textarea
    const textarea = document.getElementById("client-query");
    textarea.addEventListener("input", () => {
        textarea.style.height = "auto";
        textarea.style.height = (textarea.scrollHeight) + "px";
    });
});

// 1. Tab Navigation System
function initTabs() {
    const tabButtons = document.querySelectorAll(".tab-btn");
    const tabContents = document.querySelectorAll(".tab-content");

    tabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetTab = btn.getAttribute("data-tab");
            
            tabButtons.forEach(b => b.classList.remove("active"));
            tabContents.forEach(c => c.classList.remove("active"));
            
            btn.classList.add("active");
            document.getElementById(targetTab).classList.add("active");
            
            if (targetTab === "tab-history") {
                refreshTicketHistory();
            }
        });
    });
}

// 2. Load and Render Real-Time Inventory
async function refreshInventory() {
    const grid = document.getElementById("stock-grid");
    if (!grid) return;
    
    try {
        const response = await fetch(`${API_BASE}/api/inventory`);
        if (!response.ok) throw new Error("Fallo al obtener inventario");
        const inventory = await response.json();
        
        grid.innerHTML = "";
        
        Object.entries(inventory).forEach(([code, part]) => {
            const isOutOfStock = part.stock === 0;
            const stockBadge = isOutOfStock 
                ? `<span class="badge badge-orange"><i class="fa-solid fa-triangle-exclamation"></i> Agotado</span>`
                : `<span class="badge badge-green">${part.stock} disp.</span>`;
                
            const card = document.createElement("div");
            card.className = "stock-card";
            if (isOutOfStock) card.style.borderColor = "rgba(255, 106, 0, 0.25)";
            
            card.innerHTML = `
                <div class="stock-part-code">${code}</div>
                <div class="stock-part-name">${part.nombre}</div>
                <div class="stock-part-details">
                    <span class="stock-part-qty">${stockBadge}</span>
                    <span class="stock-part-price">$${part.precio.toFixed(2)} USD</span>
                </div>
            `;
            grid.appendChild(card);
        });
    } catch (err) {
        console.error("Error loading inventory:", err);
        grid.innerHTML = `<div class="term-line error"># Error al conectar con inventario local: ${err.message}</div>`;
    }
}

// 3. Demo Quick Case Selectors
function initDemoButtons() {
    const demoBtns = document.querySelectorAll(".btn-demo");
    const clientQuery = document.getElementById("client-query");
    
    demoBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            if (isSimulating) return;
            
            // Highlight selected button
            demoBtns.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            
            const caseId = btn.getAttribute("data-case");
            const text = DEMO_CASES[caseId];
            if (text) {
                clientQuery.value = text;
                clientQuery.dispatchEvent(new Event("input"));
                
                // If the user selected an ambiguous case, reset active ticket so it starts fresh
                if (caseId === "5") {
                    activeTicketId = null;
                    document.getElementById("interactive-prompt-card").classList.add("hidden");
                }
            }
        });
    });
    
    // Reset Inventory and Database Button
    const btnReset = document.getElementById("btn-reset");
    btnReset.addEventListener("click", async () => {
        if (isSimulating) return;
        if (confirm("¿Estás seguro de reiniciar el stock y vaciar las sesiones activas?")) {
            try {
                // Call simulation with reset_stock=true
                const res = await fetch(`${API_BASE}/api/simulate`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ reset_stock: true, client_input: "" })
                });
                
                if (res.ok) {
                    activeTicketId = null;
                    currentSessionHistory = [];
                    
                    // Reset UI
                    document.getElementById("active-ticket-lbl").innerText = "Ninguno";
                    document.getElementById("mcp-events-terminal").innerHTML = `<div class="term-line comment"># Base de datos y stock restablecidos a valores por defecto.</div>`;
                    document.getElementById("chat-messages").innerHTML = `<div class="chat-system-msg">No hay notificaciones activas</div>`;
                    document.getElementById("interactive-prompt-card").classList.add("hidden");
                    
                    // Reset Memory Fields
                    document.getElementById("mem-ticket-id").innerText = '"N/A"';
                    document.getElementById("mem-cliente").innerText = "{}";
                    document.getElementById("mem-tipo-solicitud").innerText = '"N/A"';
                    document.getElementById("mem-equipo").innerText = "{}";
                    document.getElementById("mem-diagnostico").innerText = "{}";
                    document.getElementById("mem-inventario").innerText = "{}";
                    document.getElementById("mem-estado-ticket").innerText = '"N/A"';
                    document.getElementById("mem-estado-ticket").className = "mem-val";
                    
                    // Reset Telemetry
                    document.getElementById("tele-latency").innerHTML = "0 <small>ms</small>";
                    document.getElementById("tele-tokens").innerHTML = "0 <small>tokens</small>";
                    document.getElementById("tele-success").innerText = "100.0%";
                    document.getElementById("tele-swarm-status").innerHTML = `<span class="badge badge-inactive">INACTIVO</span>`;
                    
                    resetGraphNodes();
                    await refreshInventory();
                    await refreshTicketHistory();
                    
                    alert("Stock e inventario restablecidos correctamente.");
                }
            } catch (err) {
                alert("Error al restablecer stock: " + err.message);
            }
        }
    });
}

// 4. Form Submissions and Submissions Handler
function initForms() {
    const form = document.getElementById("simulation-form");
    const replyBtn = document.getElementById("btn-reply");
    
    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        if (isSimulating) return;
        
        const clientInput = document.getElementById("client-query").value.trim();
        if (!clientInput) return;
        
        // Disable submission during execution
        setLoadingState(true);
        
        // Generate TKT code if not already under slot filling session
        if (!activeTicketId) {
            activeTicketId = `TKT-WEB-${Math.floor(Date.now() / 1000)}`;
        }
        
        await runSimulationTurn(activeTicketId, clientInput);
    });
    
    // Reply form for interactive prompt (slot filling)
    replyBtn.addEventListener("click", async () => {
        const responseInput = document.getElementById("interactive-response");
        const responseVal = responseInput.value.trim();
        if (!responseVal || isSimulating) return;
        
        document.getElementById("interactive-prompt-card").classList.add("hidden");
        responseInput.value = "";
        
        setLoadingState(true);
        
        // Append client response to device chat visually immediately
        appendChatBubble("cliente", responseVal);
        
        await runSimulationTurn(activeTicketId, responseVal);
    });
    
    // Allow pressing enter in interactive input
    document.getElementById("interactive-response").addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
            replyBtn.click();
        }
    });
}

// Set UI status during simulation process
function setLoadingState(loading) {
    isSimulating = loading;
    const btn = document.getElementById("btn-submit");
    const input = document.getElementById("client-query");
    
    if (loading) {
        btn.disabled = true;
        btn.innerHTML = `<span>Procesando...</span> <i class="fa-solid fa-spinner animate-spin"></i>`;
        input.disabled = true;
    } else {
        btn.disabled = false;
        btn.innerHTML = `<span>Enviar Consulta al Swarm</span> <i class="fa-solid fa-paper-plane"></i>`;
        input.disabled = false;
    }
}

// Helper to add custom visual spins on FontAwesome
const style = document.createElement("style");
style.innerHTML = `
.animate-spin {
    animation: fa-spin 1s infinite linear;
}
`;
document.head.appendChild(style);

// 5. Send POST simulation turn request to Server Backend
async function runSimulationTurn(ticketId, inputStr) {
    try {
        const response = await fetch(`${API_BASE}/api/simulate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                ticket_id: ticketId,
                client_input: inputStr
            })
        });
        
        if (!response.ok) throw new Error("Error en simulación del servidor.");
        
        const result = await response.json();
        
        // Refresh real-time stock after agent modifications
        await refreshInventory();
        
        // Run Step-by-Step interactive timeline playback
        await playTimelineAnimation(result);
        
    } catch (err) {
        console.error(err);
        const terminal = document.getElementById("mcp-events-terminal");
        terminal.innerHTML += `<div class="term-line error"># Error de red/servidor: ${err.message}</div>`;
        setLoadingState(false);
    }
}

// 6. Playback agent steps and trigger animations sequentially
async function playTimelineAnimation(simulationData) {
    const { ticket_id, success, state, events, telemetry, server_duration_ms } = simulationData;
    
    activeTicketId = ticket_id;
    document.getElementById("active-ticket-lbl").innerText = ticket_id;
    
    // Clear terminal and prepare step playback
    const terminal = document.getElementById("mcp-events-terminal");
    terminal.innerHTML = `<div class="term-line comment"># Iniciando reproducción de eventos reales (Total: ${events.length})...</div>`;
    
    resetGraphNodes();
    
    // Check if it's a Swarm parallel step (reparacion flow)
    const hasSwarm = state.tipo_solicitud === "reparacion";
    const swarmStatusBadge = document.getElementById("tele-swarm-status");
    
    // Update basic ticket tags
    document.getElementById("mem-ticket-id").innerText = `"${ticket_id}"`;
    
    // Step by step timeline execution play
    for (let i = 0; i < events.length; i++) {
        const ev = events[i];
        const timestamp = new Date(ev.timestamp).toLocaleTimeString();
        
        // 1. Log event details to terminal
        const termLine = document.createElement("div");
        termLine.className = "term-line info";
        
        let accentClass = "info";
        if (ev.evento === "ticket.error") accentClass = "error";
        else if (ev.evento === "reparacion.completada" || ev.evento === "venta.procesada") accentClass = "success";
        else if (ev.evento === "inventario.verificado" && !state.inventario.disponible) accentClass = "warning";
        
        termLine.className = `term-line ${accentClass}`;
        termLine.innerHTML = `[${timestamp}] <strong>${ev.evento}</strong> publicado por <strong>${ev.agente_emisor}</strong>`;
        
        // Add JSON payload details expandable
        const payloadBlock = document.createElement("pre");
        payloadBlock.className = "term-json";
        payloadBlock.innerText = JSON.stringify(ev.payload, null, 2);
        termLine.appendChild(payloadBlock);
        
        terminal.appendChild(termLine);
        terminal.scrollTop = terminal.scrollHeight;
        
        // 2. Animate Agent Nodes & Connecting Lines
        animateGraphActivity(ev, state);
        
        // 3. Update Simulated phone if event is triggered by "notificaciones"
        if (ev.agente_emisor === "notificaciones" && ev.payload && ev.payload.mensaje_cliente) {
            const canal = state.cliente.canal_preferido || "whatsapp";
            updateDeviceChannelStyle(canal);
            
            // Set contact name
            document.getElementById("notify-client-name").innerText = state.cliente.nombre || "Cliente";
            
            // Add notification bubble to screen
            appendChatBubble("notificaciones", ev.payload.mensaje_cliente, timestamp, canal);
        }
        
        // Pulse Swarm card in Telemetry if parallel Swarm is executing
        if (hasSwarm && (ev.evento === "ticket.creado" || ev.evento === "inventario.verificado")) {
            swarmStatusBadge.innerHTML = `<span class="badge badge-orange"><i class="fa-solid fa-arrows-spin animate-spin"></i> PARALELO ACTIVO</span>`;
        }
        
        // Delay between timeline steps to wow the user with visual sequence
        await delay(1200);
    }
    
    // Finished timeline playback!
    resetGraphNodes();
    
    // 4. Update the complete Shared Memory Tab view instantly
    updateSharedMemoryTab(state);
    
    // 5. Render Final Telemetry Cards
    document.getElementById("tele-latency").innerHTML = `${server_duration_ms} <small>ms</small>`;
    document.getElementById("tele-tokens").innerHTML = `${telemetry.total_tokens} <small>tokens</small>`;
    
    const successRate = telemetry.success_rate * 100;
    document.getElementById("tele-success").innerText = `${successRate.toFixed(1)}%`;
    
    if (state.next_step === "reparar_equipo") {
        swarmStatusBadge.innerHTML = `<span class="badge badge-yellow"><i class="fa-solid fa-user-pen"></i> ESPERANDO APROBACIÓN</span>`;
        
        // Buscar el evento de notificación del presupuesto (último evento)
        const budgetNotif = [...events].reverse().find(e => e.evento === "cliente.notificado" && e.payload && e.payload.mensaje_cliente && e.payload.mensaje_cliente.includes("¿Aprueba"));
        const promptText = budgetNotif ? budgetNotif.payload.mensaje_cliente : "¿Aprueba el presupuesto?";
        
        document.getElementById("interactive-prompt-text").innerText = promptText;
        document.getElementById("interactive-prompt-card").classList.remove("hidden");
        document.getElementById("interactive-response").focus();
    } else if (state.next_step === "pedir_aclaracion") {
        swarmStatusBadge.innerHTML = `<span class="badge badge-yellow"><i class="fa-solid fa-user-pen"></i> INCOMPLETO</span>`;
        
        // Buscar el evento de aclaración solicitada (último evento)
        const aclEvent = [...events].reverse().find(e => e.evento === "ticket.aclaracion_solicitada");
        const promptText = aclEvent ? aclEvent.payload.respuesta_cliente : "Se requiere aclaración del cliente.";
        
        document.getElementById("interactive-prompt-text").innerText = promptText;
        document.getElementById("interactive-prompt-card").classList.remove("hidden");
        document.getElementById("interactive-response").focus();
    } else if (success) {
        swarmStatusBadge.innerHTML = `<span class="badge badge-green"><i class="fa-solid fa-circle-check"></i> RESUELTO</span>`;
        // Si ya finalizó, limpiamos el activeTicketId para nuevas consultas
        if (state.estado_ticket === "entregado" || state.estado_ticket === "venta_procesada" || state.estado_ticket === "resuelto_remoto" || state.estado_ticket === "cancelado") {
            activeTicketId = null;
        }
    } else {
        swarmStatusBadge.innerHTML = `<span class="badge badge-orange"><i class="fa-solid fa-circle-xmark"></i> FALLADO</span>`;
    }
    
    // Re-enable form
    setLoadingState(false);
    
    // Auto refresh history list so it updates with latest state
    refreshTicketHistory();
}

// 7. Graph Node Highlight controller
function animateGraphActivity(event, state) {
    resetGraphNodes();
    
    const activeAgent = event.agente_emisor;
    const node = document.getElementById(`node-${activeAgent}`);
    if (node) {
        node.classList.add("active");
        const statusEl = node.querySelector(".node-status");
        if (statusEl) statusEl.innerText = "Activo";
    }
    
    // Highlight Orchestrator as coordinator on every step
    const orchestratorNode = document.getElementById("node-orquestador");
    orchestratorNode.classList.add("active");
    orchestratorNode.querySelector(".node-status").innerText = "Procesando";
    
    // Dynamic Active Connecting lines Glow
    const line = document.getElementById(`edge-orquestador-${activeAgent}`);
    if (line) {
        line.classList.add("active");
    }
    
    // If parallel Swarm is executing (Técnico + Almacén verifying together)
    if (event.evento === "ticket.creado" && state.tipo_solicitud === "reparacion") {
        const tecnicoNode = document.getElementById("node-tecnico_diagnostico");
        const almacenNode = document.getElementById("node-almacen");
        
        tecnicoNode.classList.add("active-swarm");
        almacenNode.classList.add("active-swarm");
        tecnicoNode.querySelector(".node-status").innerText = "Paralelo";
        almacenNode.querySelector(".node-status").innerText = "Paralelo";
        
        document.getElementById("edge-tecnico-almacen").classList.add("active-swarm");
        document.getElementById("swarm-parallel-beam").classList.remove("hidden");
        
        // Position curved beam overlay
        positionSwarmBeam();
    }
}

// Reset graph visual attributes to idle defaults
function resetGraphNodes() {
    const nodes = document.querySelectorAll(".graph-node");
    nodes.forEach(n => {
        n.classList.remove("active");
        n.classList.remove("active-swarm");
        const statusEl = n.querySelector(".node-status");
        if (statusEl) {
            statusEl.innerText = n.id === "node-orquestador" ? "En espera" : "Idle";
        }
    });
    
    const lines = document.querySelectorAll(".edge-line, .edge-line-curved");
    lines.forEach(l => {
        l.classList.remove("active");
        l.classList.remove("active-swarm");
    });
    
    const beam = document.getElementById("swarm-parallel-beam");
    if (beam) beam.classList.add("hidden");
    
    // Keep active flow category badge updated
    const flowBadge = document.getElementById("active-flow-badge");
    const tipo = document.getElementById("mem-tipo-solicitud").innerText.replace(/"/g, "").trim().toLowerCase();
    
    if (tipo === "reparacion") {
        flowBadge.className = "badge badge-green";
        flowBadge.innerText = "FLUJO: REPARACIÓN (Complejo)";
    } else if (tipo === "venta") {
        flowBadge.className = "badge badge-blue";
        flowBadge.innerText = "FLUJO: VENTA (Directo)";
    } else if (tipo === "soporte") {
        flowBadge.className = "badge badge-purple";
        flowBadge.innerText = "FLUJO: SOPORTE (Remoto)";
    } else {
        flowBadge.className = "badge badge-inactive";
        flowBadge.innerText = "Sin flujo";
    }
}

// Helper to dynamically position the curved Swarm beam glow
function positionSwarmBeam() {
    const beam = document.getElementById("swarm-parallel-beam");
    const tecnico = document.getElementById("node-tecnico_diagnostico");
    const almacen = document.getElementById("node-almacen");
    if (!tecnico || !almacen || !beam) return;
    
    const tRect = tecnico.getBoundingClientRect();
    const aRect = almacen.getBoundingClientRect();
    const containerRect = tecnico.parentElement.getBoundingClientRect();
    
    // Relative coordinates
    const x1 = tRect.left - containerRect.left + (tRect.width / 2);
    const y1 = tRect.top - containerRect.top + (tRect.height / 2);
    const x2 = aRect.left - containerRect.left + (aRect.width / 2);
    const y2 = aRect.top - containerRect.top + (aRect.height / 2);
    
    // Distance and rotation angle
    const distance = Math.sqrt((x2 - x1) * (x2 - x1) + (y2 - y1) * (y2 - y1));
    const angle = Math.atan2(y2 - y1, x2 - x1) * 180 / Math.PI;
    
    beam.style.width = `${distance}px`;
    beam.style.left = `${x1}px`;
    beam.style.top = `${y1}px`;
    beam.style.transform = `rotate(${angle}deg)`;
    beam.style.transformOrigin = "0 0";
}

// 8. Update Device styling depending on preferred channel
function updateDeviceChannelStyle(channel) {
    const appBar = document.getElementById("device-app-bar");
    if (!appBar) return;
    
    appBar.className = "device-app-bar"; // clear previous
    const notifyBadge = document.getElementById("client-notification-channel");
    
    if (channel === "whatsapp") {
        appBar.classList.add("whatsapp");
        appBar.querySelector("i").className = "fa-brands fa-whatsapp text-white";
        notifyBadge.className = "badge badge-green";
        notifyBadge.innerText = "WHATSAPP";
    } else if (channel === "sms") {
        appBar.classList.add("sms");
        appBar.querySelector("i").className = "fa-solid fa-comment-sms text-white";
        notifyBadge.className = "badge badge-blue";
        notifyBadge.innerText = "SMS";
    } else {
        appBar.classList.add("email");
        appBar.querySelector("i").className = "fa-solid fa-envelope text-white";
        notifyBadge.className = "badge badge-purple";
        notifyBadge.innerText = "EMAIL";
    }
}

// Append Chat bubble to visual phone
function appendChatBubble(sender, text, timestamp = "", channel = "whatsapp") {
    const messagesArea = document.getElementById("chat-messages");
    if (!messagesArea) return;
    
    // If it's the first message, clear system placeholder
    if (messagesArea.querySelector(".chat-system-msg")) {
        messagesArea.innerHTML = "";
    }
    
    const bubble = document.createElement("div");
    
    if (sender === "cliente") {
        bubble.className = "chat-bubble bubble-sent";
        bubble.innerText = text;
    } else {
        // Format agent message beautifully
        bubble.className = "chat-bubble-custom";
        const senderLabel = channel.toUpperCase();
        
        bubble.innerHTML = `
            <div class="bubble-header">
                <span><i class="fa-solid fa-shield-halved"></i> TechServ Inc.</span>
                <span>${senderLabel}</span>
            </div>
            <div class="bubble-content">${text}</div>
        `;
    }
    
    messagesArea.appendChild(bubble);
    messagesArea.scrollTop = messagesArea.scrollHeight;
}

// 9. Update Shared Memory Tab visual code blocks
function updateSharedMemoryTab(state) {
    document.getElementById("mem-cliente").innerText = JSON.stringify(state.cliente, null, 2);
    document.getElementById("mem-tipo-solicitud").innerText = `"${state.tipo_solicitud}"`;
    document.getElementById("mem-equipo").innerText = JSON.stringify(state.equipo, null, 2);
    document.getElementById("mem-diagnostico").innerText = JSON.stringify(state.diagnostico, null, 2);
    document.getElementById("mem-inventario").innerText = JSON.stringify(state.inventario, null, 2);
    
    const statusVal = document.getElementById("mem-estado-ticket");
    statusVal.innerText = `"${state.estado_ticket}"`;
    statusVal.className = "mem-val status-badge-inline";
    
    // Color status badge depending on state value
    if (state.estado_ticket === "listo" || state.estado_ticket === "entregado") {
        statusVal.style.borderColor = "var(--neon-emerald)";
        statusVal.style.color = "var(--neon-emerald)";
        statusVal.style.background = "rgba(5, 248, 150, 0.1)";
    } else if (state.estado_ticket === "error_interno") {
        statusVal.style.borderColor = "var(--neon-pink)";
        statusVal.style.color = "var(--neon-pink)";
        statusVal.style.background = "rgba(255, 42, 122, 0.1)";
    } else if (state.estado_ticket === "recibido") {
        statusVal.style.borderColor = "var(--neon-cyan)";
        statusVal.style.color = "var(--neon-cyan)";
        statusVal.style.background = "rgba(0, 242, 254, 0.1)";
    } else {
        statusVal.style.borderColor = "var(--neon-yellow)";
        statusVal.style.color = "var(--neon-yellow)";
        statusVal.style.background = "rgba(254, 192, 6, 0.1)";
    }
}

// Small Utility functions
function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// 10. Load and Render Ticket History
async function refreshTicketHistory() {
    const listContainer = document.getElementById("history-list");
    if (!listContainer) return;
    
    try {
        const response = await fetch(`${API_BASE}/api/tickets`);
        if (!response.ok) throw new Error("Fallo al obtener el historial de tickets");
        const tickets = await response.json();
        
        if (tickets.length === 0) {
            listContainer.innerHTML = `
                <tr>
                    <td colspan="7" class="history-empty">No hay tickets guardados en la base de datos.</td>
                </tr>
            `;
            return;
        }
        
        listContainer.innerHTML = "";
        tickets.forEach(tkt => {
            const tr = document.createElement("tr");
            
            // Format request type badge
            let typeBadge = `<span class="badge badge-inactive">${tkt.tipo_solicitud.toUpperCase()}</span>`;
            if (tkt.tipo_solicitud === "reparacion") {
                typeBadge = `<span class="badge badge-green">Reparación</span>`;
            } else if (tkt.tipo_solicitud === "venta") {
                typeBadge = `<span class="badge badge-blue">Venta</span>`;
            } else if (tkt.tipo_solicitud === "soporte") {
                typeBadge = `<span class="badge badge-purple">Soporte</span>`;
            }
            
            // Format status badge
            let statusBadge = `<span class="status-badge-inline">${tkt.estado_ticket}</span>`;
            
            // Format datetime local
            let dateStr = tkt.created_at;
            try {
                const d = new Date(tkt.created_at + (tkt.created_at.includes("Z") ? "" : "Z"));
                dateStr = d.toLocaleString();
            } catch(e) {}
            
            tr.innerHTML = `
                <td class="ticket-id-cell">${tkt.ticket_id}</td>
                <td class="client-cell">${tkt.cliente_nombre}</td>
                <td>${typeBadge}</td>
                <td>${tkt.marca_modelo}</td>
                <td>${statusBadge}</td>
                <td class="date-cell">${dateStr}</td>
                <td>
                    <button class="btn-resume" data-id="${tkt.ticket_id}">
                        <i class="fa-solid fa-folder-open"></i> Retomar
                    </button>
                </td>
            `;
            
            // Add listener to the Resume button
            tr.querySelector(".btn-resume").addEventListener("click", () => {
                resumeTicket(tkt.ticket_id);
            });
            
            listContainer.appendChild(tr);
        });
    } catch (err) {
        console.error("Error loading ticket history:", err);
        listContainer.innerHTML = `
            <tr>
                <td colspan="7" class="history-empty" style="color:var(--neon-pink);">
                    Error al cargar historial: ${err.message}
                </td>
            </tr>
        `;
    }
}

// 11. Resume an existing ticket
async function resumeTicket(ticketId) {
    if (isSimulating) return;
    setLoadingState(true);
    
    try {
        const response = await fetch(`${API_BASE}/api/status?thread_id=${ticketId}`);
        if (!response.ok) throw new Error("Fallo al obtener estado del ticket");
        const data = await response.json();
        
        const { state, events } = data;
        
        // Load into UI
        await resumeTicketIntoUI(ticketId, state, events);
        
        // Fetch inventory to make sure current screen inventory is correct
        await refreshInventory();
        
        // Switch to the Shared Memory tab so the user can inspect the loaded memory
        const memTabBtn = document.querySelector('.tab-btn[data-tab="tab-memory"]');
        if (memTabBtn) memTabBtn.click();
        
    } catch (err) {
        console.error("Error resuming ticket:", err);
        alert("Error al retomar el ticket: " + err.message);
    } finally {
        setLoadingState(false);
    }
}

// 12. Load ticket state directly into UI components instantly
async function resumeTicketIntoUI(ticketId, state, events) {
    activeTicketId = ticketId;
    document.getElementById("active-ticket-lbl").innerText = ticketId;
    
    // Update basic ticket tags
    document.getElementById("mem-ticket-id").innerText = `"${ticketId}"`;
    
    // 1. Populate terminal with all event history logs instantly
    const terminal = document.getElementById("mcp-events-terminal");
    terminal.innerHTML = `<div class="term-line success"># Ticket ${ticketId} recuperado exitosamente con ${events.length} eventos.</div>`;
    
    events.forEach(ev => {
        const timestamp = new Date(ev.timestamp).toLocaleTimeString();
        const termLine = document.createElement("div");
        
        let accentClass = "info";
        if (ev.evento === "ticket.error") accentClass = "error";
        else if (ev.evento === "reparacion.completada" || ev.evento === "venta.procesada") accentClass = "success";
        else if (ev.evento === "inventario.verificado" && state.inventario && !state.inventario.disponible) accentClass = "warning";
        
        termLine.className = `term-line ${accentClass}`;
        termLine.innerHTML = `[${timestamp}] <strong>${ev.evento}</strong> publicado por <strong>${ev.agente_emisor}</strong>`;
        
        const payloadBlock = document.createElement("pre");
        payloadBlock.className = "term-json";
        payloadBlock.innerText = JSON.stringify(ev.payload, null, 2);
        termLine.appendChild(payloadBlock);
        
        terminal.appendChild(termLine);
    });
    terminal.scrollTop = terminal.scrollHeight;
    
    // 2. Reset and animate graph nodes
    resetGraphNodes();
    
    // 3. Update Simulated phone chat history
    const canal = state.cliente.canal_preferido || "whatsapp";
    updateDeviceChannelStyle(canal);
    document.getElementById("notify-client-name").innerText = state.cliente.nombre || "Cliente";
    
    const messagesArea = document.getElementById("chat-messages");
    messagesArea.innerHTML = "";
    
    // Reconstruct conversation from historial_conversacion
    const conversation = state.historial_conversacion || [];
    if (conversation.length === 0) {
        messagesArea.innerHTML = `<div class="chat-system-msg">No hay notificaciones activas</div>`;
    } else {
        conversation.forEach(msg => {
            if (msg.role === "user") {
                appendChatBubble("cliente", msg.content);
            } else {
                appendChatBubble("notificaciones", msg.content, "", canal);
            }
        });
    }
    
    // 4. Update Shared Memory Tab
    updateSharedMemoryTab(state);
    
    // 5. Update Telemetry
    const real_tokens = Object.values(state.token_usage || {}).reduce((acc, val) => acc + val, 0);
    document.getElementById("tele-latency").innerHTML = `N/A <small>(resumido)</small>`;
    document.getElementById("tele-tokens").innerHTML = `${real_tokens} <small>tokens</small>`;
    
    const swarmStatusBadge = document.getElementById("tele-swarm-status");
    
    // 6. Handle interactive prompts depending on next_step
    if (state.next_step === "reparar_equipo") {
        swarmStatusBadge.innerHTML = `<span class="badge badge-yellow"><i class="fa-solid fa-user-pen"></i> ESPERANDO APROBACIÓN</span>`;
        
        // Find budget message (latest event)
        const budgetNotif = [...events].reverse().find(e => e.evento === "cliente.notificado" && e.payload && e.payload.mensaje_cliente && e.payload.mensaje_cliente.includes("¿Aprueba"));
        const promptText = budgetNotif ? budgetNotif.payload.mensaje_cliente : "¿Aprueba el presupuesto?";
        
        document.getElementById("interactive-prompt-text").innerText = promptText;
        document.getElementById("interactive-prompt-card").classList.remove("hidden");
        document.getElementById("interactive-response").focus();
    } else if (state.next_step === "pedir_aclaracion") {
        swarmStatusBadge.innerHTML = `<span class="badge badge-yellow"><i class="fa-solid fa-user-pen"></i> INCOMPLETO</span>`;
        
        // Find clarification message (latest event)
        const aclEvent = [...events].reverse().find(e => e.evento === "ticket.aclaracion_solicitada");
        const promptText = aclEvent ? aclEvent.payload.respuesta_cliente : "Se requiere aclaración del cliente.";
        
        document.getElementById("interactive-prompt-text").innerText = promptText;
        document.getElementById("interactive-prompt-card").classList.remove("hidden");
        document.getElementById("interactive-response").focus();
    } else if (state.estado_ticket === "entregado" || state.estado_ticket === "venta_procesada" || state.estado_ticket === "resuelto_remoto") {
        swarmStatusBadge.innerHTML = `<span class="badge badge-green"><i class="fa-solid fa-circle-check"></i> RESUELTO</span>`;
        document.getElementById("interactive-prompt-card").classList.add("hidden");
        activeTicketId = null;
    } else if (state.estado_ticket === "cancelado") {
        swarmStatusBadge.innerHTML = `<span class="badge badge-orange"><i class="fa-solid fa-circle-xmark"></i> CANCELADO</span>`;
        document.getElementById("interactive-prompt-card").classList.add("hidden");
        activeTicketId = null;
    } else {
        swarmStatusBadge.innerHTML = `<span class="badge badge-inactive">INACTIVO</span>`;
        document.getElementById("interactive-prompt-card").classList.add("hidden");
    }
}
