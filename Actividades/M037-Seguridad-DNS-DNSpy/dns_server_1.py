#!/usr/bin/python3
# Archivo ....: dns_server_1.py
# Descripcion : Servidor DNS de prueba para la practica DNSpy (exfiltracion por DNS)

import socket
import dns.message
import dns.name
import dns.rdata
import dns.rdataclass
import dns.rdatatype
import dns.rrset

servidor = "0.0.0.0"
puerto = 53
buffer = 4096
dominio = "secreto.com."
ip_respuesta = "4.3.2.1"

server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind((servidor, puerto))

print("Esperando peticion(es) DNS...")

while True:
    request_data, client_address = server_socket.recvfrom(buffer)
    request = dns.message.from_wire(request_data)

    print("Recibida peticion DNS de", client_address)
    print(request)

    full_domain_name = request.question[0].name.to_text()
    print("Nombre dominio completo: " + full_domain_name)
    subdomain = full_domain_name.split(".")[0]
    print("Subdominio recibido: " + subdomain)

    try:
        datosreales = bytes.fromhex(subdomain).decode()
        print("Mensaje oculto recibido: " + datosreales)
    except Exception as e:
        print("No hay datos en hexadecimal")

    response = dns.message.make_response(request)
    response.id = request.id
    response.set_rcode(dns.rcode.NOERROR)

    response.answer.append(dns.rrset.from_text(dominio,
                                               300,
                                               dns.rdataclass.IN,
                                               dns.rdatatype.A,
                                               ip_respuesta))

    response_data = response.to_wire()
    server_socket.sendto(response_data, client_address)
