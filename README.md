# SII – Sesión 04: Plataformas middleware

Solución de la actividad de la Sesión 04 del curso **Sistemas de Información Integrados** (UPAO, 2026-20).
Docente: Ing. Carlos Alfredo Mendoza Corpus.

**Grupo 5 – Sistema de Gestión Hotelera con IA (módulo CRM)**

- Aguilar Idrogo, Clever Josué
- Carranza Jacinto, Juan Diego
- Castillo Pezo, Mateo Salvador Vincenzo
- Romero Uriol, Jeffry Anderson
- Vidal Rodríguez, Fabrizio

## Contenido

| Carpeta | Caso | Descripción |
|---|---|---|
| `mensajeria/` | Caso 1 | Mensajería entre varias personas con transferencia de archivos. Un servidor intermediario (broker) enruta los mensajes: middleware orientado a mensajes (MOM). |
| `excel-access/` | Caso 2 | Conexión de Microsoft Excel con la base de datos `VERDULEROS.mdb` mediante Power Query y el proveedor OLE DB de Access (ACE). Incluye el libro resultante y las capturas del procedimiento. |
| `diccionario/` | Caso 3 | Formulario en Python para consultar el significado de palabras: las 49 de la sopa de letras del Laboratorio 03 y 52 términos seleccionados de la sesión S04. |
| `docs/` | Todos | Informe en PDF con la documentación de los cinco casos (incluye Yape y el ensayo). |

## Requisitos

- Python 3.8 o superior. Solo se usa la biblioteca estándar (`socket`, `threading`, `json`, `tkinter`); no hay que instalar paquetes.
- Microsoft Excel 2016 o superior (Microsoft 365 recomendado) para el caso 2.

## Caso 1 – Mensajería (middleware orientado a mensajes)

```bash
cd mensajeria
python servidor.py              # 1) iniciar el servidor (puerto 5050)
python cliente.py               # 2) abrir un cliente por cada persona
```

En cada cliente se escribe la IP del servidor (`127.0.0.1` si es la misma PC, o la IP local de quien ejecuta el servidor si están en la misma red), el puerto y un nombre. Luego se puede:

- enviar mensajes a todos o, eligiendo un usuario en **Para**, en privado;
- enviar archivos de hasta 10 MB con **Enviar archivo…** (se guardan en `recibidos/<nombre>/`);
- dejar mensajes privados a un usuario desconectado: el servidor los guarda en cola y los entrega cuando vuelve a conectarse.

El servidor registra la actividad en `servidor.log`.

| Archivo | Función |
|---|---|
| `protocolo.py` | Formato de las tramas: encabezado de 4 bytes con la longitud + JSON en UTF-8. |
| `servidor.py` | Broker: sesiones, validación de mensajes (gestor de contratos), enrutamiento, cola de pendientes y registro. |
| `cliente.py` | Interfaz gráfica (Tkinter) de cada usuario. |

> Si se prueba entre varias computadoras, puede ser necesario permitir el puerto 5050 en el firewall de Windows en la PC que ejecuta el servidor.

## Caso 2 – Excel y Access

Abrir `excel-access/Conexion_Excel_VERDULEROS.xlsx`. Las consultas de Power Query leen `VERDULEROS.mdb` y cargan sus tablas y la consulta *Consulta de ventas* en el modelo de datos; la hoja muestra una tabla dinámica y un gráfico con los kilos vendidos por vendedor y grupo de producto.

Como la ruta del archivo `.mdb` queda guardada en la consulta, al abrir el libro en otra PC hay que actualizarla en **Datos → Obtener datos → Configuración de origen de datos → Cambiar origen** y luego **Actualizar todo**.

El procedimiento completo y las capturas están en `excel-access/capturas/` y en el informe.

## Caso 3 – Diccionario

```bash
cd diccionario
python diccionario.py
```

Se escribe una palabra y se presiona **Buscar** (o Enter). La búsqueda no distingue mayúsculas ni tildes, filtra la lista mientras se escribe y sugiere palabras parecidas si no encuentra la solicitada. El botón **Buscar en Wikipedia** consulta en línea las palabras que no están en el listado.
