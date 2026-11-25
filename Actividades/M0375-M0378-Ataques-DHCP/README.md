# M0375/M0378/MC037 — Ataques DHCP: Starvation y Rogue DHCP Server

**Fecha de inicio:** 25/11/2026
**Estado:** 🔶 En progreso
**Módulos:** M0375 Servicios de red e Internet · M0378 Seguridad y alta disponibilidad · MC037 Seguridad en sistemas, redes y servicios

## Objetivo

Montar un laboratorio aislado en el cluster Proxmox del centro para practicar ataques de capa 2 contra el protocolo DHCP:

- **DHCP starvation**: agotar el pool de direcciones de un servidor DHCP enviando muchas peticiones `DHCPDISCOVER` con direcciones MAC falsas.
- **Rogue DHCP server**: levantar un servidor DHCP no autorizado que responda a los clientes antes que el legítimo.

Todo el entorno está **completamente separado de la red real del instituto**, para no interferir con ningún equipo del centro.

## Entorno de pruebas

Cluster Proxmox del centro (`cluster-fp`), nodos **nodo2** y **pau**.

| Máquina | Tipo | VMID | Nodo físico | Rol | Red | IP |
|---|---|---|---|---|---|---|
| kali-pau | VM (Kali Linux) | 103 | pau | Atacante | `vmbr1` (aislada) | 192.168.50.10/24 |
| alpine-victima | LXC (Alpine 3.24) | 104 | pau | Víctima | `vmbr1` (aislada) | DHCP (sin servidor aún) |

El bridge **`vmbr1`** es una red interna del nodo `pau`, sin salida física a la red del centro ni a internet. Es la red donde se ejecutará el ataque.

---

## ✅ Lo que hemos hecho

### Infraestructura

**VM atacante: `kali-pau` (VMID 103)**
- 2 vCPU, 4 GB RAM, 32 GB disco, sin entorno gráfico.
- Usuario `pau` / contraseña `123456`.
- Instalación base de Kali con el conjunto de paquetes "top10 + default".
- **`eth0`** en `vmbr1` (red aislada), IP `192.168.50.10/24`, sin gateway ni DNS — por diseño, para mantenerla aislada de la red real.
- **`eth1`** en `vmbr0` (red real del centro), IP `192.168.135.150/24`, gateway `192.168.135.1`, DNS `8.8.8.8`. Se añadió para dar salida a internet puntual y poder actualizar el sistema e instalar herramientas que no estaban disponibles sin conexión. Configuración permanente en `/etc/network/interfaces.d/eth1` (sobrevive a reinicios). Se puede retirar desde Proxmox cuando no se necesite salida a internet, para que la Kali quede totalmente aislada de nuevo.
- Idioma del sistema: `es_ES.UTF-8`.
- Acceso por SSH habilitado (`openssh-server`), para evitar los problemas de mapeo de teclado de la consola web de Proxmox (símbolos `; - /` mal interpretados por diferencia de idioma de teclado).

**VM víctima: `alpine-victima` (CT 104)**
- Contenedor LXC sin privilegios, plantilla **Alpine Linux 3.24** (descargada del catálogo oficial de Proxmox).
- 1 núcleo, 512 MiB RAM, 8 GiB disco.
- **`eth0`** en `vmbr1` (misma red aislada que la Kali), IP por **DHCP**.
- Usuario `root` / contraseña `123456`.
- Al arrancar, el cliente DHCP de Alpine (`udhcpc`) queda pidiendo IP sin recibir respuesta, porque `vmbr1` no tiene ningún servidor DHCP: es la situación de partida para lanzar el ataque.

### Pasos realizados

1. Se detectó que `kali-pau` solo tenía `eth0` en `vmbr1` (red aislada, sin DNS ni gateway), por lo que no tenía forma de instalar `yersinia` ni `dhcpstarv`.
2. Se añadió una segunda interfaz de red (`net1`) en `vmbr0` desde Proxmox, y se configuró con IP fija `192.168.135.150/24` + gateway + DNS, primero a mano y después de forma permanente mediante un archivo en `/etc/network/interfaces.d/`.
3. Se actualizó el sistema (`apt full-upgrade`). Durante la actualización surgió un conflicto de `dpkg` entre los paquetes `pyinstaller-hooks-contrib` y `python3-pyinstaller-hooks-contrib` (renombrado de paquete con archivos duplicados), resuelto forzando la sobrescritura de archivos:
   ```bash
   sudo apt -o Dpkg::Options::="--force-overwrite" --fix-broken install -y
   sudo apt -o Dpkg::Options::="--force-overwrite" full-upgrade -y
   ```
4. Se generó y activó el idioma `es_ES.UTF-8` (`dpkg-reconfigure locales`).
5. Se instalaron las herramientas de ataque DHCP:
   ```bash
   sudo apt install -y yersinia dhcpstarv
   ```
6. Se creó la VM víctima: contenedor LXC Alpine 3.24 (`alpine-victima`, CT 104) en `vmbr1`, con red por DHCP, para que reciba el ataque de forma aislada.

---

## 🔜 Lo que vamos a hacer

1. **Escribir el script de ataque en Python con `scapy`**, con dos modos:
   - *DHCP starvation*: construir y enviar en bucle paquetes `DHCPDISCOVER` con una dirección MAC origen aleatoria distinta en cada envío, para agotar el rango de direcciones de un servidor DHCP legítimo.
   - *Rogue DHCP server*: escuchar peticiones `DHCPDISCOVER`/`DHCPREQUEST` en `vmbr1` y responder con `DHCPOFFER`/`DHCPACK` suplantando a un servidor legítimo (pudiendo entregar una puerta de enlace o DNS controlados por el atacante).
2. **Ejecutar el ataque** desde `kali-pau` contra `alpine-victima`, comprobando en la víctima con `udhcpc -i eth0 -f -v` qué ofertas recibe y de quién.
3. **Capturar evidencias** del tráfico DHCP durante el ataque con `tcpdump`/Wireshark en ambas máquinas.
4. **Documentar los resultados** en este README: salida de los scripts, capturas de pantalla y análisis de las tramas DHCP capturadas.
5. **Tareas arrastradas de la actividad anterior** (DNS tunneling):
   - Añadir aquí o en [M037-Seguridad-DNS-DNSpy](../M037-Seguridad-DNS-DNSpy) las capturas de Wireshark pendientes.
   - Borrar el `captura_cliente.iso` suelto en *Datacenter → pau → local → Imágenes ISO*.

## Notas de seguridad

Todo el ataque se ejecuta dentro de `vmbr1`, una red interna sin salida física ni a la red del centro ni a internet. La interfaz `eth1` de `kali-pau` (con salida a la red real) solo se activa puntualmente para tareas de mantenimiento (actualizar, instalar paquetes) y debe eliminarse o mantenerse desconectada mientras no se necesite, para que el laboratorio permanezca aislado durante las pruebas de ataque.
