"""
protocolo.py - Formato de las tramas que viajan entre clientes y servidor.

Cada mensaje es un objeto JSON codificado en UTF-8 y precedido por un
encabezado de 4 bytes (entero sin signo, big-endian) con su longitud.
Así el receptor sabe exactamente cuántos bytes leer, aunque TCP entregue
los datos en trozos.

    +----------------+------------------------------+
    | longitud (4 B) | JSON (UTF-8)                 |
    +----------------+------------------------------+

Tipos de mensaje (campo "tipo"):
    registro      cliente -> servidor   {"nombre"}
    bienvenida    servidor -> cliente   {"nombre", "usuarios"}
    error         servidor -> cliente   {"texto"}
    texto         ambos sentidos        {"de", "para", "texto", "hora"}
    archivo       ambos sentidos        {"de", "para", "nombre_archivo", "tamano", "datos"(base64), "hora"}
    usuarios      servidor -> cliente   {"usuarios"}
    sistema       servidor -> cliente   {"texto", "hora"}
    salir         cliente -> servidor   {}

"para" vale "*" para todos (difusión) o el nombre de un usuario (privado).
"""

import json
import struct

ENCABEZADO = struct.Struct("!I")          # 4 bytes, big-endian
TAMANO_MAX_TRAMA = 16 * 1024 * 1024       # 16 MB por trama
TAMANO_MAX_ARCHIVO = 10 * 1024 * 1024     # 10 MB por archivo
PUERTO_POR_DEFECTO = 5050
TODOS = "*"


def enviar(sock, mensaje: dict) -> None:
    """Serializa el diccionario a JSON y lo envía con su encabezado."""
    datos = json.dumps(mensaje, ensure_ascii=False).encode("utf-8")
    sock.sendall(ENCABEZADO.pack(len(datos)) + datos)


def _leer_exacto(sock, n: int) -> bytes:
    """Lee exactamente n bytes o devuelve b'' si la conexión se cerró."""
    partes = []
    faltan = n
    while faltan > 0:
        trozo = sock.recv(min(faltan, 65536))
        if not trozo:
            return b""
        partes.append(trozo)
        faltan -= len(trozo)
    return b"".join(partes)


def recibir(sock):
    """Devuelve el siguiente mensaje (dict) o None si la conexión terminó."""
    cabecera = _leer_exacto(sock, ENCABEZADO.size)
    if not cabecera:
        return None
    (longitud,) = ENCABEZADO.unpack(cabecera)
    if longitud > TAMANO_MAX_TRAMA:
        raise ValueError(f"Trama demasiado grande: {longitud} bytes")
    cuerpo = _leer_exacto(sock, longitud)
    if not cuerpo:
        return None
    return json.loads(cuerpo.decode("utf-8"))
