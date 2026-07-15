# Manual de Resolución de Problemas Típicos y Tarifario de Servicios

Este manual contiene los procedimientos de diagnóstico y soluciones recomendadas para 30 problemas frecuentes de hardware, red y software, asociando a cada uno un repuesto o servicio tasado para asegurar que los presupuestos nunca tengan costo de materiales cero.

---

## 1. Problemas de Arranque y Encendido

- **Caso 1: PC enciende (ventiladores giran) pero pantalla en negro ("No Signal")**
  - **Diagnóstico**: RAM mal colocada, GPU suelta o BIOS desconfigurada.
  - **Solución**: Limpiar pines de RAM, resetear BIOS retirando la pila CMOS.
  - **Componente/Servicio**: `Servicio_Mantenimiento_Contactos` y `Pila_CR2032`.

- **Caso 2: Pantalla azul 0x0000007B (INACCESSIBLE_BOOT_DEVICE)**
  - **Diagnóstico**: Controlador de disco incorrecto, modo SATA cambiado de AHCI a IDE.
  - **Solución**: Cambiar modo en BIOS a AHCI o reparar MBR/BCD desde recovery.
  - **Componente/Servicio**: `Servicio_Recuperacion_Sistema`.

- **Caso 3: PC se apaga 2 segundos después de encender**
  - **Diagnóstico**: Cortocircuito en placa base, fuente de poder defectuosa o standoffs.
  - **Solución**: Hacer puente en fuente (paperclip test) y revisar aislamiento de standoffs.
  - **Componente/Servicio**: `Servicio_Aislamiento_Placa` o `Fuente_Poder`.

- **Caso 4: Windows se queda congelado en el logo (círculo de puntos girando)**
  - **Diagnóstico**: Archivos de arranque corruptos o sectores defectuosos en el disco.
  - **Solución**: Ejecutar comandos SFC /scannow y chkdsk en consola de recuperación.
  - **Componente/Servicio**: `SSD_1TB` o `Servicio_Recuperacion_Sistema`.

---

## 2. Rendimiento y Temperatura

- **Caso 5: Uso de disco al 100% en Administrador de Tareas**
  - **Diagnóstico**: Fallo en SysMain (SuperFetch) o disco duro mecánico dañado.
  - **Solución**: Deshabilitar SysMain y Windows Search. Reemplazar disco por SSD.
  - **Componente/Servicio**: `SSD_1TB`.

- **Caso 6: CPU al 100% sin programas abiertos ("System Interrupts")**
  - **Diagnóstico**: Controladores de red o audio incompatibles o defectuosos.
  - **Solución**: Desconectar periféricos USB y actualizar drivers del chipset.
  - **Componente/Servicio**: `Servicio_Optimizacion_Drivers`.

- **Caso 7: Frecuencia de CPU baja a 0.8 GHz (Thermal Throttling)**
  - **Diagnóstico**: Sobrecalentamiento extremo por pasta térmica seca o polvo.
  - **Solución**: Limpiar disipadores de calor y reaplicar pasta térmica.
  - **Componente/Servicio**: `Pasta_Termica` y `Ventilador_CPU`.

- **Caso 8: Memoria RAM consumida al 90% en reposo (Memory Leak)**
  - **Diagnóstico**: Fuga de memoria por drivers de red ("Killer Control Center").
  - **Solución**: Desinstalar software de red problemático y dejar driver plano.
  - **Componente/Servicio**: `Servicio_Limpieza_Software` o expansión a `RAM_16GB`.

---

## 3. Conectividad y Redes

- **Caso 9: WiFi conectado pero con mensaje "Sin Internet, protegida"**
  - **Diagnóstico**: Fallo de asignación DHCP o DNS caído del ISP.
  - **Solución**: Ejecutar ipconfig /release y ipconfig /renew, cambiar DNS a 8.8.8.8.
  - **Componente/Servicio**: `Servicio_Configuracion_Red`.

- **Caso 10: Cable Ethernet conectado pero muestra "Red no identificada"**
  - **Diagnóstico**: Dirección IP duplicada o fallo en protocolo TCP/IP de Windows.
  - **Solución**: Resetear sockets con netsh winsock reset y asignar IP fija temporal.
  - **Componente/Servicio**: `Servicio_Configuracion_Red`.

- **Caso 11: Adaptador WiFi desapareció del Administrador de Dispositivos**
  - **Diagnóstico**: Falla física de la tarjeta o bloqueo de energía por Windows Update.
  - **Solución**: Mostrar dispositivos ocultos, desinstalar driver y drenar energía de la placa.
  - **Componente/Servicio**: `Tarjeta_WiFi_PCIe`.

- **Caso 12: Ping alto y pérdida de paquetes en WiFi**
  - **Diagnóstico**: Interferencia de frecuencias de 2.4 GHz o saturación de canales.
  - **Solución**: Cambiar canal del router al 1, 6 u 11 o cambiar a banda de 5 GHz.
  - **Componente/Servicio**: `Servicio_Configuracion_Red`.

---

## 4. Pantalla y Gráficos

- **Caso 13: Pantalla parpadea con líneas horizontales al mover ventanas**
  - **Diagnóstico**: Frecuencia de refresco incompatible o memoria VRAM dañada.
  - **Solución**: Configurar refresco a 60Hz y estresar GPU con FurMark.
  - **Componente/Servicio**: `Tarjeta_Grafica_GPU`.

- **Caso 14: Colores lavados o exceso de brillo blanco en el monitor**
  - **Diagnóstico**: HDR activado de forma errónea en pantallas no soportadas.
  - **Solución**: Desactivar HDR en ajustes de pantalla de Windows.
  - **Componente/Servicio**: `Cable_HDMI_2.0`.

---

## 5. Audio y Multimedia

- **Caso 15: No hay sonido en parlantes pero sí en auriculares**
  - **Diagnóstico**: Sensor Jack de audio frontal atascado mecánicamente.
  - **Solución**: Desactivar detección de jack frontal en consola Realtek.
  - **Componente/Servicio**: `Servicio_Reparacion_Jack`.

- **Caso 16: El sonido se corta o hace "chisporroteo" (crackling) en juegos**
  - **Diagnóstico**: Latencia DPC causada por controladores obsoletos de video.
  - **Solución**: Ajustar administración de energía de PCIe y actualizar drivers de sonido.
  - **Componente/Servicio**: `Servicio_Optimizacion_Audio`.

---

## 6. Periféricos y Puertos

- **Caso 17: Ventana emergente "Dispositivo USB no reconocido" constantemente**
  - **Diagnóstico**: Puerto USB en cortocircuito físico o driver del chipset dañado.
  - **Solución**: Desinstalar controladores de raíz USB en Administrador de Dispositivos.
  - **Componente/Servicio**: `Hub_USB_Externo`.

- **Caso 18: Disco externo se lee como "Disco Local" RAW y pide formatear**
  - **Diagnóstico**: Tabla de particiones del disco dañada por desconexión insegura.
  - **Solución**: Ejecutar chkdsk para reparar sectores y recuperar tabla con TestDisk.
  - **Componente/Servicio**: `Servicio_Recuperacion_Datos`.

- **Caso 19: Teclado escribe caracteres extraños (ej: layout cambiado)**
  - **Diagnóstico**: Cambio de idioma de entrada accidental (US-International/ES).
  - **Solución**: Cambiar layout con Win+Espacio y remover layouts sobrantes.
  - **Componente/Servicio**: `Servicio_Configuracion_Teclado` o reemplazo por `Teclado_Bluetooth`.

- **Caso 20: Impresora muestra "Sin conexión" (Offline) por USB**
  - **Diagnóstico**: Cola de impresión bloqueada o servicio Print Spooler caído.
  - **Solución**: Reiniciar servicio Spooler y desactivar "Trabajar sin conexión".
  - **Componente/Servicio**: `Servicio_Soporte_Impresora`.

---

## 7. Software y Sistema Operativo

- **Caso 21: Aplicaciones se cierran solas con código de error 0xC0000005**
  - **Diagnóstico**: Conflicto de acceso a memoria por antivirus o memoria RAM con fallos.
  - **Solución**: Desactivar temporalmente el antivirus y ejecutar mdsched.exe.
  - **Componente/Servicio**: `Servicio_Diagnostico_Software` o `RAM_8GB`.

- **Caso 22: Descargas de Windows Update bloqueadas en 0%**
  - **Diagnóstico**: Carpeta de caché de actualizaciones corrupta.
  - **Solución**: Detener wuauserv, limpiar SoftwareDistribution y reiniciar servicios.
  - **Componente/Servicio**: `Servicio_Diagnostico_Software`.

- **Caso 23: Mensaje de error diciendo "Falta VCRUNTIME140.dll"**
  - **Diagnóstico**: Faltan las librerías necesarias de Microsoft Visual C++.
  - **Solución**: Instalar los paquetes redistribuibles de Visual C++ x86 y x64.
  - **Componente/Servicio**: `Servicio_Instalacion_Librerias`.

- **Caso 24: Navegadores llenos de anuncios invasivos y páginas de inicio cambiadas**
  - **Diagnóstico**: Extensión maliciosa (hijacker) o archivo Hosts alterado.
  - **Solución**: Eliminar extensiones, resetear Chrome y limpiar hosts de Windows.
  - **Componente/Servicio**: `Servicio_Limpieza_Malware`.

- **Caso 25: Disco C: lleno en rojo pero sin archivos visibles grandes**
  - **Diagnóstico**: Archivos temporales ocultos o archivo de hibernación exagerado.
  - **Solución**: Deshabilitar hibernación con powercfg -h off y liberar archivos del sistema.
  - **Componente/Servicio**: `Servicio_Limpieza_Disco`.

- **Caso 26: Transferencia de archivos a USB muy lenta (menos de 1MB/s)**
  - **Diagnóstico**: Dispositivo conectado en puerto USB 2.0 o formateado en FAT32.
  - **Solución**: Usar puerto 3.0 (azul) y formatear a NTFS o exFAT para optimizar caché.
  - **Componente/Servicio**: `Pendrive_USB_3.0`.

- **Caso 27: Windows indica "8 GB instalados (4 GB usable)"**
  - **Diagnóstico**: Sistema de 32 bits instalado o exceso de RAM asignado a iGPU.
  - **Solución**: Instalar Windows de 64 bits y modificar reservas de iGPU en BIOS.
  - **Componente/Servicio**: `Licencia_Windows_11_64bit`.

---

## 8. Fallas Generales de Hardware

- **Caso 28: PC se apaga o reinicia aleatoriamente al jugar sin pantallazo azul**
  - **Diagnóstico**: Fuente de alimentación con potencia insuficiente para la GPU.
  - **Solución**: Reemplazar fuente por una de mayor wattage certificado.
  - **Componente/Servicio**: `Fuente_Poder`.

- **Caso 29: La hora de Windows se reinicia a fecha antigua al apagar el equipo**
  - **Diagnóstico**: Pila CMOS CR2032 de la placa madre agotada.
  - **Solución**: Reemplazar físicamente la pila botón CR2032 en la placa.
  - **Componente/Servicio**: `Pila_CR2032`.

- **Caso 30: Ventilador de CPU hace mucho ruido y gira al 100% constantemente**
  - **Diagnóstico**: Cabezal configurado en DC en lugar de PWM en BIOS.
  - **Solución**: Entrar a BIOS y cambiar modo del ventilador a PWM.
  - **Componente/Servicio**: `Ventilador_CPU`.
