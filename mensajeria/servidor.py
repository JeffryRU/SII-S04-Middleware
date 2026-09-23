"""
servidor.py - Intermediario (broker) de mensajería: middleware orientado a mensajes.

Los clientes nunca se conectan entre sí: todos hablan con este servidor,
que recibe cada mensaje, valida su formato (gestor de contratos), decide a
quién entregarlo (enrutamiento) y lo reenvía. Si el destinatario de un
mensaje privado no está conectado, el mensaje se guarda en una cola y se
entrega cuando vuelva a conectarse (almacenar y reenviar).

Uso:
    python servidor.py                 # escucha en 0.0.0.0:5050
    python servidor.py --puerto 6000
"""

from __future__ import annotations

import argparse
import datetime as dt
import socket
import threading
from collections import defaultdict, deque

import protocolo as p

TIPOS_PERMITIDOS = {"registro", "texto", "archivo", "salir"}


def ahora() -> str:
    return dt.datetime.now().strftime("%H:%M:%S")


class Servidor:
    def __init__(self, host: str, puerto: int, archivo_log: str = "servidor.log"):
        self.host = host
        self.puerto = puerto
        self.clientes = {}                      # nombre -> socket
        self.bloqueos = {}                      # nombre -> candado de envío (evita mezclar tramas)
        self.conocidos = set()                  # usuarios que alguna vez se registraron
        self.pendientes = defaultdict(deque)    # nombre -> cola de mensajes no entregados
        self.candado = threading.Lock()
        self.log = open(archivo_log, "a", encoding="utf-8")

    # ------------------------------------------------------------------ registro
    def registrar(self, evento: str) -> None:
        linea = f"[{dt.datetime.now():%Y-%m-%d %H:%M:%S}] {evento}"
        print(linea)
        self.log.write(linea + "\n")
        self.log.flush()

    # ------------------------------------------------------------------ envío
    def _enviar_seguro(self, nombre: str, mensaje: dict) -> bool:
        with self.candado:
            sock = self.clientes.get(nombre)
            bloqueo = self.bloqueos.get(nombre)
        if sock is None:
            return False
        try:
            with bloqueo:
                p.enviar(sock, mensaje)
            return True
        except OSError:
            return False

    def difundir(self, mensaje: dict, excepto: str | None = None) -> None:
        with self.candado:
            destinos = [n for n in self.clientes if n != excepto]
        for nombre in destinos:
            self._enviar_seguro(nombre, mensaje)

    def enviar_lista_usuarios(self) -> None:
        with self.candado:
            usuarios = sorted(self.clientes)
        self.difundir({"tipo": "usuarios", "usuarios": usuarios})

    def aviso(self, texto: str, excepto: str | None = None) -> None:
        self.difundir({"tipo": "sistema", "texto": texto, "hora": ahora()}, excepto)

    # ------------------------------------------------------------------ contrato
    @staticmethod
    def validar(mensaje) -> str | None:
        """Gestor de contratos: devuelve un texto de error o None si es válido."""
        if not isinstance(mensaje, dict) or mensaje.get("tipo") not in TIPOS_PERMITIDOS:
            return "Tipo de mensaje no permitido."
        tipo = mensaje["tipo"]
        if tipo == "texto":
            if not isinstance(mensaje.get("texto"), str) or not mensaje["texto"].strip():
                return "El texto no puede estar vacío."
            if len(mensaje["texto"]) > 4000:
                return "El texto supera los 4000 caracteres."
        if tipo == "archivo":
            if not mensaje.get("nombre_archivo") or not isinstance(mensaje.get("datos"), str):
                return "Archivo incompleto."
            if int(mensaje.get("tamano", 0)) > p.TAMANO_MAX_ARCHIVO:
                return "El archivo supera los 10 MB."
        return None

    # ------------------------------------------------------------------ enrutamiento
    def enrutar(self, origen: str, mensaje: dict) -> None:
        mensaje["de"] = origen
        mensaje["hora"] = ahora()
        destino = mensaje.get("para") or p.TODOS
        descripcion = (mensaje.get("nombre_archivo") and f"archivo '{mensaje['nombre_archivo']}' "
                       f"({mensaje.get('tamano', 0)} B)") or "texto"

        if destino == p.TODOS:
            self.difundir(mensaje, excepto=origen)
            self.registrar(f"{origen} -> todos: {descripcion}")
            return

        with self.candado:
            conectado = destino in self.clientes
            existe = destino in self.conocidos
        if conectado:
            self._enviar_seguro(destino, mensaje)
            self.registrar(f"{origen} -> {destino}: {descripcion}")
        elif existe:
            with self.candado:
                self.pendientes[destino].append(mensaje)
            self._enviar_seguro(origen, {"tipo": "sistema", "hora": ahora(),
                                         "texto": f"{destino} no está conectado; "
                                                  "el mensaje quedó en cola y se entregará al volver."})
            self.registrar(f"{origen} -> {destino}: {descripcion} (en cola)")
        else:
            self._enviar_seguro(origen, {"tipo": "error", "texto": f"El usuario '{destino}' no existe."})

    # ------------------------------------------------------------------ sesión de un cliente
    def atender(self, sock: socket.socket, direccion) -> None:
        nombre = None
        try:
            primero = p.recibir(sock)
            if not primero or primero.get("tipo") != "registro":
                p.enviar(sock, {"tipo": "error", "texto": "Primero debe registrarse."})
                return
            nombre = str(primero.get("nombre", "")).strip()[:20]
            with self.candado:
                ocupado = (not nombre) or nombre == p.TODOS or nombre in self.clientes
                if not ocupado:
                    self.clientes[nombre] = sock
                    self.bloqueos[nombre] = threading.Lock()
                    self.conocidos.add(nombre)
            if ocupado:
                p.enviar(sock, {"tipo": "error", "texto": "Nombre vacío o ya en uso."})
                nombre = None
                return

            self.registrar(f"Conexión de {nombre} desde {direccion[0]}:{direccion[1]}")
            with self.candado:
                usuarios = sorted(self.clientes)
            self._enviar_seguro(nombre, {"tipo": "bienvenida", "nombre": nombre, "usuarios": usuarios})
            self.aviso(f"{nombre} se unió al chat.", excepto=nombre)
            self.enviar_lista_usuarios()

            # Entregar mensajes que quedaron en cola mientras estaba desconectado
            with self.candado:
                cola = self.pendientes.pop(nombre, deque())
            for pendiente in cola:
                self._enviar_seguro(nombre, pendiente)

            while True:
                mensaje = p.recibir(sock)
                if mensaje is None or mensaje.get("tipo") == "salir":
                    break
                error = self.validar(mensaje)
                if error:
                    self._enviar_seguro(nombre, {"tipo": "error", "texto": error})
                    continue
                self.enrutar(nombre, mensaje)
        except (OSError, ValueError) as exc:
            self.registrar(f"Error con {nombre or direccion}: {exc}")
        finally:
            if nombre:
                with self.candado:
                    self.clientes.pop(nombre, None)
                    self.bloqueos.pop(nombre, None)
                self.registrar(f"Desconexión de {nombre}")
                self.aviso(f"{nombre} salió del chat.")
                self.enviar_lista_usuarios()
            try:
                sock.close()
            except OSError:
                pass

    # ------------------------------------------------------------------ bucle principal
    def iniciar(self) -> None:
        escucha = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        escucha.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        escucha.bind((self.host, self.puerto))
        escucha.listen()
        self.registrar(f"Servidor de mensajería escuchando en {self.host}:{self.puerto}")
        try:
            while True:
                sock, direccion = escucha.accept()
                threading.Thread(target=self.atender, args=(sock, direccion), daemon=True).start()
        except KeyboardInterrupt:
            self.registrar("Servidor detenido.")
        finally:
            escucha.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Servidor de mensajería (middleware MOM)")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--puerto", type=int, default=p.PUERTO_POR_DEFECTO)
    args = parser.parse_args()
    Servidor(args.host, args.puerto).iniciar()
