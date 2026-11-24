# M037 — Seguridad en el DNS: Exfiltración de datos por DNS (DNSpy)

**Fecha:** 24/11/2026
**Módulo:** MC037 Seguridad en sistemas, redes y servicios

## Objetivo

Análisis e implementación de una técnica de exfiltración de datos mediante el protocolo DNS (DNS tunneling), ocultando información arbitraria en el campo de subdominio de una consulta DNS y codificándola en hexadecimal.

## Entorno de pruebas

Se ha usado el cluster Proxmox del centro (`cluster-fp`), formado por dos nodos: **nodo2** y **pau**, accesibles vía Netbird.

Para cumplir el requisito de ejecutar cliente y servidor en dos máquinas distintas con IPs diferentes, se han creado dos contenedores LXC (Debian 12), uno en cada nodo del cluster, conectados al mismo bridge `vmbr0` con IP asignada por DHCP:

| Contenedor | VMID | Nodo físico | IP |
|---|---|---|---|
| dns-server-pau | 100 | nodo2 | 192.168.135.29 |
| dns-client-pau | 102 | pau | 192.168.135.32 |

Ambos en la misma subred, pero en nodos físicos distintos del cluster, lo que demuestra el funcionamiento real entre dos equipos separados.

## Preparación

1. Se descargó la plantilla `debian-12-standard_12.12-1_amd64.tar.zst` desde el catálogo oficial de Proxmox en el storage `local` de **nodo2**.
2. Se creó el contenedor **dns-server-pau** (VMID 100) en **nodo2**, red `vmbr0` con IP por DHCP.
3. Se creó el contenedor **dns-client-pau** (VMID 102) en **pau**, misma red, misma plantilla (ya disponible en el storage local de ese nodo).
4. En ambos contenedores se instaló la librería `python3-dnspython` (paquete oficial de Debian) y `tcpdump` para la captura de tráfico.
5. Se transcribieron los scripts proporcionados ([`dns_server_1.py`](./dns_server_1.py) y [`dns_client_1.py`](./dns_client_1.py)) adaptando la IP del servidor en el cliente y quitando el `break` del servidor para que pueda atender más de una petición.

## Script servidor DNS

Escucha en el puerto 53/UDP. Por cada petición recibida:

1. Extrae el nombre de dominio completo de la pregunta DNS.
2. Toma el primer subdominio (la parte antes del primer punto), que es donde viaja el dato oculto.
3. Intenta decodificarlo de hexadecimal a texto (`bytes.fromhex(...).decode()`).
4. Responde siempre con el mismo registro A (`4.3.2.1`) para confirmar la recepción al cliente.

Ver código completo: [`dns_server_1.py`](./dns_server_1.py)

## Script cliente DNS

Codifica el mensaje a exfiltrar en hexadecimal, lo coloca como subdominio de un dominio ficticio (`secreto.com`) y envía una consulta de registro A al servidor. El mensaje `"datos ocultos"` en hexadecimal es `6461746f73206f63756c746f73`.

Ver código completo: [`dns_client_1.py`](./dns_client_1.py)

## Ejecución de la prueba y capturas

Se lanzó `tcpdump -i eth0 -nn port 53` en ambos contenedores simultáneamente (guardando `.pcap`), se arrancó el servidor en dns-server-pau y se ejecutó el cliente en dns-client-pau.

**Salida del cliente (dns-client-pau, 192.168.135.32):**
```
Inicio del envio
Respuesta:  id 3391
opcode QUERY
rcode NOERROR
flags QR RD
;QUESTION
6461746f73206f63756c746f73.secreto.com. IN A
;ANSWER
secreto.com. 300 IN A 4.3.2.1
Fin del envio
```

**Salida del servidor (dns-server-pau, 192.168.135.29):**
```
Esperando peticion(es) DNS...
Recibida peticion DNS de ('192.168.135.32', 51972)
Nombre dominio completo: 6461746f73206f63756c746f73.secreto.com.
Subdominio recibido: 6461746f73206f63756c746f73
Mensaje oculto recibido: datos ocultos
```

**Captura de tráfico (`tcpdump -r captura_servidor.pcap`):** se observan las dos tramas, la petición del cliente (192.168.135.32 → 192.168.135.29, puerto 53, con el subdominio hexadecimal en claro dentro del payload) y la respuesta del servidor con el registro A `4.3.2.1`.

> Los ficheros `captura_servidor.pcap` y `captura_cliente.pcap` quedan guardados en `/root/` de cada contenedor. Pendiente: copiarlos y añadir aquí capturas de pantalla de Wireshark con el detalle de ambas tramas.

## Conclusiones

Se ha demostrado de forma práctica una técnica de exfiltración de datos mediante el protocolo DNS (DNS tunneling), ocultando información arbitraria en el campo de subdominio de una consulta y codificándola en hexadecimal para evitar caracteres no válidos en un nombre de dominio.

La prueba se ha realizado entre dos máquinas físicamente distintas del cluster (nodo2 y pau), cada una con su propia IP, cumpliendo el requisito del enunciado de no limitarse a un entorno localhost.

Esta técnica es relevante en seguridad porque el tráfico DNS suele estar permitido por los firewalls perimetrales incluso cuando otros protocolos están bloqueados, lo que la convierte en un canal encubierto habitual en ataques reales de exfiltración de datos o comunicación con servidores de mando y control (C2).
