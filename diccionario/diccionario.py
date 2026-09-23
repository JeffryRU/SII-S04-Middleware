"""
diccionario.py - Formulario de consulta de términos (Sistemas de Información Integrados).

Permite buscar una palabra y mostrar su significado. El listado reúne:
  * Las 49 palabras de la sopa de letras "Sistemas verticales y horizontales"
    (Laboratorio 03).
  * Términos técnicos seleccionados de la presentación S04_SII (Plataformas
    middleware, ESB y plataformas de integración).

Características:
  - Búsqueda sin distinguir mayúsculas ni tildes ("analisis" encuentra "ANÁLISIS").
  - Lista filtrable (todas / Lab 03 / S04) que se actualiza mientras se escribe.
  - Sugerencias de palabras parecidas si el término no existe.
  - Consulta opcional en Wikipedia en español para palabras fuera del listado
    (requiere Internet; el resto funciona sin conexión).

Requisitos: Python 3.8 o superior (solo usa la biblioteca estándar).
Uso:        python diccionario.py
"""

from __future__ import annotations

import difflib
import json
import threading
import tkinter as tk
import unicodedata
import urllib.parse
import urllib.request
from tkinter import ttk

LAB03 = "Laboratorio 03 - Sopa de letras"
S04 = "S04 - Plataformas middleware"

# --------------------------------------------------------------------------------------
# Palabras de la sopa de letras "Sistemas verticales y horizontales" (Laboratorio 03)
# --------------------------------------------------------------------------------------
PALABRAS_LAB03 = {
    "ACCESO": "Capacidad de un usuario autorizado para ingresar a un sistema o dato; se controla con autenticación y roles.",
    "ACTUALIZACIÓN": "Nueva versión o parche de un software que corrige errores, mejora la seguridad o añade funciones.",
    "ADAPTACIÓN": "Ajuste de una aplicación (sobre todo horizontal) a los procesos concretos de una empresa.",
    "AGILIDAD": "Capacidad de la organización o del equipo de responder rápido a los cambios; base de Scrum y Kanban.",
    "ALMACENAMIENTO": "Conservación persistente de datos en discos, servidores o la nube.",
    "ANÁLISIS": "Estudio de requerimientos, procesos o datos para tomar decisiones o diseñar un sistema.",
    "AUTOMATIZACIÓN": "Ejecución de tareas repetitivas por software sin intervención humana; beneficio común de ERP, CRM y SCM.",
    "BASE DE DATOS": "Conjunto organizado de datos gestionado por un SGBD; ejemplo clásico de aplicación horizontal.",
    "BENEFICIOS": "Ventajas medibles que aporta un sistema: menos costos, más productividad, mejor servicio.",
    "CLÍNICAS": "Sector salud; ejemplo de mercado vertical (software de historias clínicas).",
    "COLABORACIÓN": "Trabajo conjunto entre áreas o equipos apoyado en información compartida; objetivo del ERP.",
    "COMPATIBILIDAD": "Capacidad de un software de funcionar e intercambiar datos con otros sistemas o plataformas.",
    "COMPROMISO": "Implicación del personal y de la dirección con el proyecto; también se fortalece con el onboarding.",
    "COMUNICACIÓN": "Intercambio de información entre personas, áreas o sistemas (APIs, integraciones).",
    "CONSOLIDACIÓN": "Unificación de datos de varias fuentes o sedes en una sola vista (p. ej., estados financieros).",
    "CONSULTORÍA": "Servicio experto que asesora en la selección, implantación y mejora de sistemas.",
    "COSTE": "Inversión necesaria para adquirir, implantar y mantener un sistema (licencias, soporte, capacitación).",
    "CRECIMIENTO": "Expansión del negocio; el sistema debe acompañarlo sin rehacerse (escalabilidad).",
    "DECISIONES": "Elecciones de gestión que se apoyan en reportes e indicadores en tiempo real.",
    "DESARROLLO": "Proceso de construir software: análisis, diseño, programación y pruebas.",
    "DIGITAL": "Información o procesos representados y gestionados por medios electrónicos.",
    "DOCUMENTACIÓN": "Manuales, especificaciones y registros que describen un sistema y su uso.",
    "EFICACIA": "Grado en que se logran los objetivos planteados.",
    "ESCALABILIDAD": "Capacidad del sistema de soportar más usuarios, datos o sedes sin perder rendimiento.",
    "ESTRATEGIA": "Plan de largo plazo que orienta la elección de tecnología y los objetivos del negocio.",
    "HISTORIAS": "Historias clínicas (sector salud) o historias de usuario (requisitos ágiles).",
    "HOJA DE CÁLCULO": "Aplicación horizontal para cálculo tabular (Excel, Google Sheets).",
    "IMPLEMENTACIÓN": "Puesta en marcha de un sistema: instalación, configuración, migración y capacitación.",
    "INFORMES": "Documentos que resumen datos del sistema para control y toma de decisiones.",
    "INNOVACIÓN": "Introducción de mejoras o tecnologías nuevas (IA, IoT) que generan valor.",
    "INTEGRADOS": "Sistemas que comparten datos y procesos en una base común, como un ERP.",
    "INTERFAZ": "Punto de interacción entre usuario y sistema (UI) o entre sistemas (API).",
    "MÓDULOS": "Componentes funcionales de un ERP/CRM (finanzas, RR. HH., inventario, ventas).",
    "OBJETIVOS": "Metas concretas y medibles que el proyecto o la empresa busca alcanzar.",
    "OPTIMIZACIÓN": "Mejora de un proceso para obtener más resultado con menos recursos.",
    "PARÁMETROS": "Valores configurables que adaptan una aplicación híbrida sin reprogramarla.",
    "PARTNER": "Socio tecnológico que implanta, personaliza y da soporte a una solución (p. ej., partner SAP).",
    "PERSONALIZACIÓN": "Modificación del software para ajustarlo a requerimientos particulares del cliente.",
    "PLANES": "Planificación (la «P» de ERP) o modalidades de suscripción/licencia de un software.",
    "PREDICCIÓN": "Estimación de eventos futuros (demanda, fallas) con analítica o IA; típica del SCM.",
    "PROYECTO": "Esfuerzo temporal con alcance, tiempo y costo definidos para crear un producto o servicio.",
    "REDUCCIÓN": "Disminución de costos, tiempos o errores lograda con la automatización.",
    "RENTABILIDAD": "Relación entre el beneficio obtenido y la inversión realizada (ROI).",
    "REPORTES": "Salidas de información periódicas o en tiempo real para control y gestión.",
    "RESULTADOS": "Efectos medibles obtenidos tras implantar un sistema o ejecutar un proceso.",
    "SEGUIMIENTO": "Monitoreo continuo del avance de un proyecto, cliente o pedido.",
    "SEGURIDAD": "Protección de la confidencialidad, integridad y disponibilidad de la información.",
    "SOCIOS": "Aliados estratégicos (proveedores, partners) con los que la empresa colabora.",
    "TRANSFORMACIÓN": "Transformación digital: rediseño del negocio apoyado en tecnología.",
}

# --------------------------------------------------------------------------------------
# Términos seleccionados de S04_SII.pdf (palabras que no conocíamos o no dominábamos)
# --------------------------------------------------------------------------------------
PALABRAS_S04 = {
    "MIDDLEWARE": "Software intermedio que permite que aplicaciones, bases de datos y servicios distintos se comuniquen entre sí como si fueran un solo sistema.",
    "MOM": "Middleware orientado a mensajes (Message-Oriented Middleware): intercambia mensajes entre aplicaciones mediante colas o agentes (brokers), gestionando su enrutamiento y orden de entrega.",
    "RPC": "Llamada a procedimiento remoto (Remote Procedure Call): permite ejecutar una función en otra computadora como si fuera local.",
    "ORB": "Object Request Broker: intermediario que recibe la petición de un objeto y la hace cumplir por otro objeto ubicado en cualquier lugar de la red.",
    "CORBA": "Common Object Request Broker Architecture: estándar del OMG para que objetos escritos en distintos lenguajes y plataformas se comuniquen mediante un ORB.",
    "TPM": "Monitor de procesamiento de transacciones (Transaction Processing Monitor): middleware transaccional que lleva cada transacción de un paso al siguiente hasta completarla o revertirla.",
    "MIDDLEWARE TRANSACCIONAL": "Middleware que garantiza que las transacciones distribuidas se ejecuten completas o no se ejecuten (atomicidad), por ejemplo mediante un TPM.",
    "MIDDLEWARE DE PORTAL": "Middleware que integra contenido y funciones de varias aplicaciones en una sola pantalla o aplicación compuesta.",
    "ESB": "Bus de servicios empresarial (Enterprise Service Bus): componente centralizado que conecta aplicaciones, transforma datos, enruta mensajes y convierte protocolos.",
    "SOA": "Arquitectura orientada a servicios: diseño en el que las funciones del negocio se exponen como servicios reutilizables con interfaces estándar.",
    "iPaaS": "Integration Platform as a Service: plataforma de integración en la nube para conectar aplicaciones, datos y procesos (p. ej., MuleSoft, Dell Boomi, SAP Integration Suite).",
    "PaaS": "Platform as a Service: nube que ofrece un entorno para crear, ejecutar y gestionar aplicaciones sin administrar la infraestructura.",
    "SaaS": "Software as a Service: aplicación que se usa por Internet mediante suscripción, sin instalarla (p. ej., Salesforce, Microsoft 365).",
    "MWaaS": "Middleware as a Service: middleware ofrecido como servicio en la nube para facilitar la integración y comunicación entre sistemas.",
    "API": "Interfaz de programación de aplicaciones: conjunto de reglas y operaciones que un sistema expone para que otros lo usen.",
    "API GATEWAY": "Puerta de enlace de API: punto único de entrada que recibe las llamadas a las API y aplica seguridad, límites de uso y enrutamiento.",
    "REST": "Representational State Transfer: estilo de arquitectura para servicios web que usa HTTP (GET, POST, PUT, DELETE) sobre recursos identificados por URL.",
    "SOAP": "Simple Object Access Protocol: protocolo de mensajería basado en XML para servicios web, con contrato formal descrito en WSDL.",
    "WSDL": "Web Services Description Language: documento XML que describe las operaciones, mensajes y dirección de un servicio web.",
    "JSON": "JavaScript Object Notation: formato de texto ligero para intercambiar datos con pares clave-valor.",
    "XML": "Extensible Markup Language: lenguaje de marcado con etiquetas para representar y transportar datos estructurados.",
    "ENDPOINT": "Dirección concreta (URL y método) donde un servicio o API recibe solicitudes.",
    "APACHE KAFKA": "Plataforma de código abierto para transmitir eventos en tiempo real; ejemplo de middleware de transmisión de datos asíncrona.",
    "ASÍNCRONO": "Comunicación en la que el emisor no espera la respuesta inmediata del receptor para seguir trabajando.",
    "ENRUTAMIENTO": "Decisión de a qué destino debe entregarse cada mensaje según su contenido o reglas definidas.",
    "ACOPLAMIENTO": "Grado de dependencia entre componentes; un acoplamiento débil permite cambiar uno sin afectar a los demás.",
    "ORQUESTACIÓN": "Coordinación centralizada de varios servicios o contenedores para ejecutar un proceso completo.",
    "CONECTOR": "Adaptador prediseñado que enlaza una plataforma de integración con un sistema específico (ERP, CRM, base de datos).",
    "GESTOR DE CONTRATOS": "Componente del middleware que define las reglas de intercambio de datos y devuelve una excepción si una aplicación las incumple.",
    "GESTOR DE SESIONES": "Componente del middleware que establece un canal seguro con cada aplicación y registra su actividad.",
    "DATA PIPELINE": "Canal por el que los datos pasan de una aplicación a otra a través del middleware, que los procesa para hacerlos compatibles.",
    "SISTEMA HEREDADO": "Sistema antiguo (legacy) que sigue operando y que se integra con aplicaciones nuevas en lugar de reemplazarse.",
    "MAINFRAME": "Computadora central de gran capacidad usada por bancos y grandes empresas para procesar muchas transacciones.",
    "MICROSERVICIOS": "Arquitectura que divide una aplicación en servicios pequeños e independientes que se comunican por API o mensajes.",
    "CONTENEDOR": "Paquete ligero con el código de una aplicación y sus dependencias, que se ejecuta igual en cualquier infraestructura (p. ej., Docker).",
    "KUBERNETES": "Plataforma de código abierto para orquestar contenedores: despliegue, escalado y recuperación automática.",
    "NATIVO DE LA NUBE": "Enfoque que diseña aplicaciones con microservicios y contenedores para aprovechar la nube desde el inicio.",
    "NUBE HÍBRIDA": "Combinación de infraestructura local, nube privada y nube pública gestionadas de forma conjunta.",
    "MULTINUBE": "Uso de servicios de varios proveedores de nube (AWS, Azure, Google Cloud) al mismo tiempo.",
    "ON-PREMISES": "Software instalado y operado en los servidores propios de la organización, no en la nube.",
    "CSP": "Cloud Service Provider: proveedor de servicios en la nube, como Microsoft Azure, Google Cloud, AWS o IBM Cloud.",
    "DEVOPS": "Cultura y prácticas que unen desarrollo y operaciones para entregar software de forma rápida y continua.",
    "DEVSECOPS": "Extensión de DevOps que incorpora la seguridad en todas las etapas del desarrollo y la operación.",
    "CI/CD": "Integración continua y entrega continua: automatización de la compilación, pruebas y despliegue del software.",
    "TLS": "Transport Layer Security: protocolo criptográfico que cifra la comunicación entre aplicaciones (base de HTTPS).",
    "SERVERLESS": "Computación sin servidor: el proveedor de nube ejecuta el código bajo demanda y el cliente no administra servidores.",
    "LOW-CODE": "Desarrollo con poco código, usando componentes visuales y configuraciones en lugar de programar todo a mano.",
    "CONFIANZA CERO": "Modelo de seguridad (zero trust) que no confía en ningún acceso por defecto y verifica cada solicitud.",
    "SILOS DE DATOS": "Datos aislados en un área o sistema que no se comparten con el resto de la organización.",
    "GOBERNANZA": "Conjunto de políticas y controles que regulan el ciclo de vida de los servicios, datos o API.",
    "CAGR": "Compound Annual Growth Rate: tasa de crecimiento anual compuesta de un mercado o indicador.",
    "INTEROPERABILIDAD": "Capacidad de sistemas diferentes para intercambiar información y usarla correctamente.",
}

DICCIONARIO = {**{k: (v, LAB03) for k, v in PALABRAS_LAB03.items()},
               **{k: (v, S04) for k, v in PALABRAS_S04.items()}}


def normalizar(texto: str) -> str:
    """Mayúsculas y sin tildes, para comparar sin importar cómo se escribió."""
    sin_tildes = "".join(c for c in unicodedata.normalize("NFD", texto)
                         if unicodedata.category(c) != "Mn")
    return " ".join(sin_tildes.upper().split())


INDICE = {normalizar(k): k for k in DICCIONARIO}


def buscar(termino: str):
    """Devuelve (palabra, significado, fuente) o None."""
    clave = INDICE.get(normalizar(termino))
    if clave is None:
        return None
    significado, fuente = DICCIONARIO[clave]
    return clave, significado, fuente


def sugerencias(termino: str, n: int = 5):
    t = normalizar(termino)
    parecidas = difflib.get_close_matches(t, INDICE.keys(), n=n, cutoff=0.6)
    contienen = [k for k in INDICE if t and t in k and k not in parecidas]
    return [INDICE[k] for k in (parecidas + contienen)[:n]]


def buscar_wikipedia(termino: str) -> str | None:
    """Resumen de Wikipedia en español (opcional, requiere Internet)."""
    url = ("https://es.wikipedia.org/api/rest_v1/page/summary/"
           + urllib.parse.quote(termino.strip().replace(" ", "_")))
    peticion = urllib.request.Request(url, headers={"User-Agent": "DiccionarioSII/1.0 (UPAO)"})
    with urllib.request.urlopen(peticion, timeout=6) as r:
        datos = json.loads(r.read().decode("utf-8"))
    return datos.get("extract") or None


class Formulario:
    def __init__(self, raiz: tk.Tk):
        self.raiz = raiz
        raiz.title("Diccionario SII - Consulta de términos")
        raiz.geometry("860x520")
        raiz.minsize(700, 440)

        cabecera = ttk.Frame(raiz, padding=(12, 10))
        cabecera.pack(fill="x")
        ttk.Label(cabecera, text="Diccionario de Sistemas de Información Integrados",
                  font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ttk.Label(cabecera, text=f"{len(PALABRAS_LAB03)} palabras del Laboratorio 03 + "
                                 f"{len(PALABRAS_S04)} términos de la sesión S04 "
                                 f"= {len(DICCIONARIO)} en total").pack(anchor="w")

        # Barra de búsqueda
        barra = ttk.Frame(raiz, padding=(12, 4))
        barra.pack(fill="x")
        ttk.Label(barra, text="Palabra:").pack(side="left")
        self.var_busqueda = tk.StringVar()
        self.var_busqueda.trace_add("write", lambda *_: self.filtrar())
        self.entrada = ttk.Entry(barra, textvariable=self.var_busqueda, font=("Segoe UI", 11))
        self.entrada.pack(side="left", fill="x", expand=True, padx=6)
        self.entrada.bind("<Return>", lambda _e: self.consultar())
        ttk.Button(barra, text="Buscar", command=self.consultar).pack(side="left", padx=2)
        ttk.Button(barra, text="Limpiar", command=self.limpiar).pack(side="left", padx=2)
        self.btn_web = ttk.Button(barra, text="Buscar en Wikipedia", command=self.consultar_web,
                                  state="disabled")
        self.btn_web.pack(side="left", padx=2)

        cuerpo = ttk.Frame(raiz, padding=12)
        cuerpo.pack(fill="both", expand=True)

        # Lista de palabras
        izquierda = ttk.LabelFrame(cuerpo, text="Listado", padding=6)
        izquierda.pack(side="left", fill="y")
        self.var_fuente = tk.StringVar(value="Todas")
        combo = ttk.Combobox(izquierda, textvariable=self.var_fuente, state="readonly", width=24,
                             values=["Todas", LAB03, S04])
        combo.pack(fill="x", pady=(0, 6))
        combo.bind("<<ComboboxSelected>>", lambda _e: self.filtrar())
        marco_lista = ttk.Frame(izquierda)
        marco_lista.pack(fill="y", expand=True)
        self.lista = tk.Listbox(marco_lista, width=28, exportselection=False, font=("Segoe UI", 10))
        barra_lista = ttk.Scrollbar(marco_lista, command=self.lista.yview)
        self.lista.configure(yscrollcommand=barra_lista.set)
        self.lista.pack(side="left", fill="y", expand=True)
        barra_lista.pack(side="left", fill="y")
        self.lista.bind("<<ListboxSelect>>", self.seleccionar)
        self.lista.bind("<Double-Button-1>", self.seleccionar)
        self.var_contador = tk.StringVar()
        ttk.Label(izquierda, textvariable=self.var_contador).pack(anchor="w", pady=(4, 0))

        # Resultado
        derecha = ttk.LabelFrame(cuerpo, text="Significado", padding=10)
        derecha.pack(side="left", fill="both", expand=True, padx=(10, 0))
        self.var_palabra = tk.StringVar(value="Escriba una palabra y presione Buscar")
        ttk.Label(derecha, textvariable=self.var_palabra, font=("Segoe UI", 16, "bold"),
                  wraplength=460).pack(anchor="w")
        self.var_origen = tk.StringVar()
        ttk.Label(derecha, textvariable=self.var_origen, foreground="#555555").pack(anchor="w", pady=(2, 8))
        self.texto = tk.Text(derecha, wrap="word", height=10, font=("Segoe UI", 11), relief="flat",
                             background=raiz.cget("background"))
        self.texto.pack(fill="both", expand=True)
        self.texto.configure(state="disabled")

        self.filtrar()
        self.entrada.focus_set()

    # ------------------------------------------------------------------ acciones
    def mostrar(self, titulo: str, origen: str, cuerpo: str):
        self.var_palabra.set(titulo)
        self.var_origen.set(origen)
        self.texto.configure(state="normal")
        self.texto.delete("1.0", "end")
        self.texto.insert("1.0", cuerpo)
        self.texto.configure(state="disabled")

    def filtrar(self):
        fuente = self.var_fuente.get()
        t = normalizar(self.var_busqueda.get())
        self.lista.delete(0, "end")
        for palabra in sorted(DICCIONARIO, key=normalizar):
            if fuente != "Todas" and DICCIONARIO[palabra][1] != fuente:
                continue
            if t and t not in normalizar(palabra):
                continue
            self.lista.insert("end", palabra)
        self.var_contador.set(f"{self.lista.size()} palabra(s)")

    def consultar(self):
        termino = self.var_busqueda.get().strip()
        if not termino:
            return
        resultado = buscar(termino)
        if resultado:
            palabra, significado, fuente = resultado
            self.mostrar(palabra, f"Fuente: {fuente}", significado)
            self.btn_web.configure(state="disabled")
            return
        parecidas = sugerencias(termino)
        cuerpo = "La palabra no está en el listado."
        if parecidas:
            cuerpo += "\n\n¿Quiso decir?: " + ", ".join(parecidas)
        cuerpo += "\n\nPuede consultarla en Wikipedia con el botón «Buscar en Wikipedia»."
        self.mostrar(termino.upper(), "No encontrada", cuerpo)
        self.btn_web.configure(state="normal")

    def consultar_web(self):
        termino = self.var_busqueda.get().strip()
        if not termino:
            return
        self.mostrar(termino.upper(), "Consultando Wikipedia…", "")
        self.btn_web.configure(state="disabled")

        def trabajo():
            try:
                extracto = buscar_wikipedia(termino)
                texto = extracto or "Wikipedia no tiene un artículo con ese nombre."
            except Exception as exc:  # sin Internet, página inexistente, etc.
                texto = f"No se pudo consultar Wikipedia ({exc})."
            self.raiz.after(0, lambda: self.mostrar(termino.upper(), "Fuente: Wikipedia en español", texto))

        threading.Thread(target=trabajo, daemon=True).start()

    def seleccionar(self, _evento=None):
        seleccion = self.lista.curselection()
        if not seleccion:
            return
        palabra = self.lista.get(seleccion[0])
        significado, fuente = DICCIONARIO[palabra]
        self.mostrar(palabra, f"Fuente: {fuente}", significado)
        self.btn_web.configure(state="disabled")

    def limpiar(self):
        self.var_busqueda.set("")
        self.var_fuente.set("Todas")
        self.filtrar()
        self.mostrar("Escriba una palabra y presione Buscar", "", "")
        self.entrada.focus_set()


if __name__ == "__main__":
    raiz = tk.Tk()
    try:
        ttk.Style().theme_use("vista")
    except tk.TclError:
        pass
    Formulario(raiz)
    raiz.mainloop()
