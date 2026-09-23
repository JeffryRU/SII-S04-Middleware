"""
cliente.py - Cliente gráfico (Tkinter) del sistema de mensajería.

Cada persona ejecuta este programa, se conecta al servidor (el middleware)
y puede:
  - enviar mensajes a todos o en privado a un usuario de la lista;
  - enviar archivos (hasta 10 MB) a todos o a un usuario;
  - ver quién está conectado y los avisos del sistema.

Los archivos recibidos se guardan en la carpeta "recibidos/<su nombre>/".

Uso:
    python cliente.py
"""

from __future__ import annotations

import base64
import os
import queue
import socket
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import protocolo as p

CARPETA_RECIBIDOS = "recibidos"
OPCION_TODOS = "(Todos)"


class ClienteChat:
    def __init__(self, raiz: tk.Tk):
        self.raiz = raiz
        self.sock: socket.socket | None = None
        self.nombre = ""
        self.vistos = set()      # usuarios vistos en la sesión (para mensajes en cola)
        self.eventos: queue.Queue = queue.Queue()   # hilo receptor -> interfaz
        self.bloqueo_envio = threading.Lock()

        raiz.title("Mensajería SII - Middleware")
        raiz.geometry("920x560")
        raiz.minsize(640, 420)
        raiz.protocol("WM_DELETE_WINDOW", self.cerrar)
        self._construir_conexion()
        self._construir_chat()
        self.raiz.after(100, self._procesar_eventos)

    # ================================================================ interfaz
    def _construir_conexion(self):
        marco = ttk.LabelFrame(self.raiz, text="Conexión con el servidor", padding=8)
        marco.pack(fill="x", padx=10, pady=(10, 5))

        ttk.Label(marco, text="Servidor:").grid(row=0, column=0, sticky="w")
        self.var_host = tk.StringVar(value="127.0.0.1")
        ttk.Entry(marco, textvariable=self.var_host, width=16).grid(row=0, column=1, padx=4)

        ttk.Label(marco, text="Puerto:").grid(row=0, column=2, sticky="w")
        self.var_puerto = tk.StringVar(value=str(p.PUERTO_POR_DEFECTO))
        ttk.Entry(marco, textvariable=self.var_puerto, width=7).grid(row=0, column=3, padx=4)

        ttk.Label(marco, text="Su nombre:").grid(row=0, column=4, sticky="w")
        self.var_nombre = tk.StringVar()
        entrada_nombre = ttk.Entry(marco, textvariable=self.var_nombre, width=16)
        entrada_nombre.grid(row=0, column=5, padx=4)
        entrada_nombre.bind("<Return>", lambda _e: self.conectar())

        self.btn_conectar = ttk.Button(marco, text="Conectar", command=self.conectar)
        self.btn_conectar.grid(row=0, column=6, padx=4)
        self.btn_desconectar = ttk.Button(marco, text="Desconectar", command=self.desconectar,
                                          state="disabled")
        self.btn_desconectar.grid(row=0, column=7, padx=4)

    def _construir_chat(self):
        cuerpo = ttk.Frame(self.raiz, padding=(10, 0))
        cuerpo.pack(fill="both", expand=True)

        # Historial de mensajes
        izquierda = ttk.Frame(cuerpo)
        izquierda.pack(side="left", fill="both", expand=True)
        self.historial = tk.Text(izquierda, state="disabled", wrap="word", width=40,
                                 font=("Segoe UI", 10))
        barra = ttk.Scrollbar(izquierda, command=self.historial.yview)
        self.historial.configure(yscrollcommand=barra.set)
        self.historial.pack(side="left", fill="both", expand=True)
        barra.pack(side="left", fill="y")
        self.historial.tag_configure("sistema", foreground="#666666", font=("Segoe UI", 9, "italic"))
        self.historial.tag_configure("propio", foreground="#0b5394")
        self.historial.tag_configure("privado", foreground="#7f3f98")
        self.historial.tag_configure("error", foreground="#b00020")
        self.historial.tag_configure("archivo", foreground="#38761d")

        # Lista de usuarios conectados
        derecha = ttk.LabelFrame(cuerpo, text="Conectados", padding=6)
        derecha.pack(side="left", fill="y", padx=(8, 0))
        self.lista_usuarios = tk.Listbox(derecha, width=20, exportselection=False)
        self.lista_usuarios.pack(fill="y", expand=True)
        self.lista_usuarios.bind("<<ListboxSelect>>", self._seleccionar_destino)

        # Barra de envío
        pie = ttk.Frame(self.raiz, padding=10)
        pie.pack(fill="x")
        ttk.Label(pie, text="Para:").pack(side="left")
        self.var_destino = tk.StringVar(value=OPCION_TODOS)
        self.combo_destino = ttk.Combobox(pie, textvariable=self.var_destino, width=16,
                                          state="readonly", values=[OPCION_TODOS])
        self.combo_destino.pack(side="left", padx=4)
        self.var_texto = tk.StringVar()
        self.entrada = ttk.Entry(pie, textvariable=self.var_texto)
        self.entrada.pack(side="left", fill="x", expand=True, padx=4)
        self.entrada.bind("<Return>", lambda _e: self.enviar_texto())
        self.btn_enviar = ttk.Button(pie, text="Enviar", command=self.enviar_texto, state="disabled")
        self.btn_enviar.pack(side="left", padx=2)
        self.btn_archivo = ttk.Button(pie, text="Enviar archivo…", command=self.enviar_archivo,
                                      state="disabled")
        self.btn_archivo.pack(side="left", padx=2)

    def escribir(self, texto: str, etiqueta: str | None = None):
        self.historial.configure(state="normal")
        self.historial.insert("end", texto + "\n", etiqueta or ())
        self.historial.configure(state="disabled")
        self.historial.see("end")

    def _seleccionar_destino(self, _evento=None):
        seleccion = self.lista_usuarios.curselection()
        if seleccion:
            usuario = self.lista_usuarios.get(seleccion[0]).replace(" (usted)", "")
            self.var_destino.set(OPCION_TODOS if usuario == self.nombre else usuario)

    def _actualizar_usuarios(self, usuarios):
        self.lista_usuarios.delete(0, "end")
        for u in usuarios:
            self.lista_usuarios.insert("end", f"{u} (usted)" if u == self.nombre else u)
        self.vistos.update(usuarios)
        # Se listan también los usuarios desconectados: el servidor guarda sus
        # mensajes privados en cola y los entrega cuando vuelven a conectarse.
        otros = sorted(u for u in self.vistos if u != self.nombre)
        self.combo_destino["values"] = [OPCION_TODOS] + otros
        if self.var_destino.get() not in self.combo_destino["values"]:
            self.var_destino.set(OPCION_TODOS)

    def _estado_conectado(self, conectado: bool):
        normal = "normal" if conectado else "disabled"
        self.btn_enviar.configure(state=normal)
        self.btn_archivo.configure(state=normal)
        self.btn_desconectar.configure(state=normal)
        self.btn_conectar.configure(state="disabled" if conectado else "normal")

    # ================================================================ red
    def conectar(self):
        nombre = self.var_nombre.get().strip()
        if not nombre:
            messagebox.showwarning("Falta el nombre", "Escriba su nombre para identificarse.")
            return
        try:
            puerto = int(self.var_puerto.get())
            self.sock = socket.create_connection((self.var_host.get().strip(), puerto), timeout=5)
            self.sock.settimeout(None)
            p.enviar(self.sock, {"tipo": "registro", "nombre": nombre})
        except (OSError, ValueError) as exc:
            messagebox.showerror("No se pudo conectar", f"Revise que el servidor esté activo.\n\n{exc}")
            self.sock = None
            return
        self.nombre = nombre
        threading.Thread(target=self._recibir_en_segundo_plano, args=(self.sock,), daemon=True).start()

    def desconectar(self):
        if self.sock:
            try:
                self._enviar({"tipo": "salir"})
                self.sock.close()
            except OSError:
                pass
        self.sock = None
        self._estado_conectado(False)
        self._actualizar_usuarios([])
        self.escribir("Desconectado del servidor.", "sistema")

    def _recibir_en_segundo_plano(self, sock):
        """Hilo receptor: nunca toca la interfaz, solo encola eventos."""
        try:
            while True:
                mensaje = p.recibir(sock)
                if mensaje is None:
                    break
                self.eventos.put(mensaje)
        except (OSError, ValueError):
            pass
        self.eventos.put({"tipo": "_cerrado", "sock": sock})

    def _enviar(self, mensaje: dict):
        with self.bloqueo_envio:
            p.enviar(self.sock, mensaje)

    def _destino(self) -> str:
        d = self.var_destino.get()
        return p.TODOS if d in ("", OPCION_TODOS) else d

    def enviar_texto(self):
        texto = self.var_texto.get().strip()
        if not texto or not self.sock:
            return
        destino = self._destino()
        try:
            self._enviar({"tipo": "texto", "para": destino, "texto": texto})
        except OSError as exc:
            self.escribir(f"No se pudo enviar: {exc}", "error")
            return
        prefijo = "Usted" if destino == p.TODOS else f"Usted → {destino} (privado)"
        self.escribir(f"{prefijo}: {texto}", "propio")
        self.var_texto.set("")

    def enviar_archivo(self):
        if not self.sock:
            return
        ruta = filedialog.askopenfilename(title="Seleccione el archivo a enviar")
        if not ruta:
            return
        tamano = os.path.getsize(ruta)
        if tamano > p.TAMANO_MAX_ARCHIVO:
            messagebox.showwarning("Archivo muy grande", "El límite es de 10 MB por archivo.")
            return
        with open(ruta, "rb") as f:
            datos = base64.b64encode(f.read()).decode("ascii")
        destino = self._destino()
        nombre_archivo = os.path.basename(ruta)
        self.escribir(f"Enviando '{nombre_archivo}' ({tamano:,} bytes)…", "sistema")

        def trabajo():
            try:
                self._enviar({"tipo": "archivo", "para": destino, "nombre_archivo": nombre_archivo,
                              "tamano": tamano, "datos": datos})
                a_quien = "todos" if destino == p.TODOS else destino
                self.eventos.put({"tipo": "_local", "texto": f"Archivo '{nombre_archivo}' enviado a {a_quien}."})
            except OSError as exc:
                self.eventos.put({"tipo": "error", "texto": f"No se pudo enviar el archivo: {exc}"})

        threading.Thread(target=trabajo, daemon=True).start()

    def _guardar_archivo(self, mensaje: dict) -> str:
        carpeta = os.path.join(CARPETA_RECIBIDOS, self.nombre)
        os.makedirs(carpeta, exist_ok=True)
        nombre = os.path.basename(mensaje["nombre_archivo"])   # evita rutas maliciosas
        base, ext = os.path.splitext(nombre)
        ruta = os.path.join(carpeta, nombre)
        n = 1
        while os.path.exists(ruta):
            ruta = os.path.join(carpeta, f"{base}_{n}{ext}")
            n += 1
        with open(ruta, "wb") as f:
            f.write(base64.b64decode(mensaje["datos"]))
        return ruta

    # ================================================================ eventos
    def _procesar_eventos(self):
        try:
            while True:
                self._manejar(self.eventos.get_nowait())
        except queue.Empty:
            pass
        self.raiz.after(100, self._procesar_eventos)

    def _manejar(self, m: dict):
        tipo = m.get("tipo")
        hora = m.get("hora", "")
        if tipo == "bienvenida":
            self._estado_conectado(True)
            self.raiz.title(f"Mensajería SII - {self.nombre}")
            self.escribir(f"Conectado como {self.nombre}.", "sistema")
            self._actualizar_usuarios(m.get("usuarios", []))
        elif tipo == "usuarios":
            self._actualizar_usuarios(m.get("usuarios", []))
        elif tipo == "sistema":
            self.escribir(f"[{hora}] {m.get('texto', '')}", "sistema")
        elif tipo == "_local":
            self.escribir(m.get("texto", ""), "sistema")
        elif tipo == "error":
            self.escribir(f"Error: {m.get('texto', '')}", "error")
        elif tipo == "texto":
            privado = m.get("para") not in (None, p.TODOS)
            etiqueta = "privado" if privado else None
            extra = " (privado)" if privado else ""
            self.escribir(f"[{hora}] {m.get('de')}{extra}: {m.get('texto')}", etiqueta)
        elif tipo == "archivo":
            try:
                ruta = self._guardar_archivo(m)
                self.escribir(f"[{hora}] {m.get('de')} le envió '{m.get('nombre_archivo')}' "
                              f"({m.get('tamano', 0):,} bytes). Guardado en: {ruta}",
                              "archivo")
            except (OSError, ValueError) as exc:
                self.escribir(f"No se pudo guardar el archivo recibido: {exc}", "error")
        elif tipo == "_cerrado":
            if m.get("sock") is self.sock:
                self.sock = None
                self._estado_conectado(False)
                self._actualizar_usuarios([])
                self.escribir("Se cerró la conexión con el servidor.", "sistema")

    def cerrar(self):
        if self.sock:
            self.desconectar()
        self.raiz.destroy()


if __name__ == "__main__":
    raiz = tk.Tk()
    try:
        ttk.Style().theme_use("vista")
    except tk.TclError:
        pass
    ClienteChat(raiz)
    raiz.mainloop()
