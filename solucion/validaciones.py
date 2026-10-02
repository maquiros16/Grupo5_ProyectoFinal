"""Reglas del enunciado, independientes de Tkinter y SQLite."""
from datetime import datetime
import unicodedata


class ErrorValidacion(ValueError):
    """Mensaje que puede mostrarse directamente a la persona usuaria."""


# Valida el tipo de entrada y recorta espacios externos.
def normalizar_texto(valor, campo):
    if not isinstance(valor, str):
        raise ErrorValidacion(f"{campo}: debe ser texto.")
    return valor.strip()


# Comprueba la longitud y los caracteres permitidos del carné.
def validar_carne(valor):
    valor = normalizar_texto(valor, "Carné")
    if len(valor) != 10 or not valor.isalnum():
        raise ErrorValidacion("Carné: use exactamente 10 caracteres alfanuméricos, sin espacios.")
    return valor


# Obtiene la clave de comparación de un carné válido.
def clave_carne(valor):
    return validar_carne(valor).casefold()


# Comprueba el mínimo de caracteres no blancos del nombre.
def validar_nombre(valor):
    valor = normalizar_texto(valor, "Nombre")
    if sum(not caracter.isspace() for caracter in valor) < 3:
        raise ErrorValidacion("Nombre: incluya al menos tres caracteres distintos de espacios.")
    return valor


# Comprueba la presencia de un único arroba y un punto posterior.
def validar_correo(valor):
    valor = normalizar_texto(valor, "Correo")
    if valor.count("@") != 1 or "." not in valor.split("@")[-1]:
        raise ErrorValidacion("Correo: debe contener exactamente un @ y al menos un punto después.")
    return valor


# Comprueba que el código de sala no quede vacío.
def validar_codigo_sala(valor):
    valor = normalizar_texto(valor, "Código")
    if not valor:
        raise ErrorValidacion("Código: indique el código de la sala.")
    return valor


# Comprueba que la capacidad sea un entero mayor que cero.
def validar_capacidad(valor):
    valor = normalizar_texto(valor, "Capacidad")
    if not valor.isdigit() or int(valor) <= 0:
        raise ErrorValidacion("Capacidad: indique un número entero mayor que cero.")
    return int(valor)


# Restringe el estado de la sala a disponible o fuera de servicio.
def validar_estado_sala(valor):
    valor = normalizar_texto(valor, "Estado")
    if valor not in ("disponible", "fuera_de_servicio"):
        raise ErrorValidacion("Estado: seleccione disponible o fuera_de_servicio.")
    return valor


# Comprueba una fecha obligatoria en formato AAAA-MM-DD.
def validar_fecha(valor, campo):
    valor = normalizar_texto(valor, campo)
    try:
        fecha = datetime.strptime(valor, "%Y-%m-%d")
        if valor != fecha.strftime("%Y-%m-%d"):
            raise ValueError
    except ValueError:
        raise ErrorValidacion(
            f"{campo}: use una fecha válida con formato AAAA-MM-DD."
        ) from None
    return valor


# Comprueba el rango obligatorio del reporte.
def validar_rango_fechas(inicio, fin):
    inicio = validar_fecha(inicio, "Fecha inicial")
    fin = validar_fecha(fin, "Fecha final")
    if fin < inicio:
        raise ErrorValidacion("Fecha final: no puede ser anterior a la fecha inicial.")
    return inicio, fin


# Restringe el estado a activo o inactivo.
def validar_estado(valor):
    valor = normalizar_texto(valor, "Estado")
    if valor not in ("activo", "inactivo"):
        raise ErrorValidacion("Estado: seleccione activo o inactivo.")
    return valor


# Normaliza el nombre para un orden independiente de tildes y capitalización.
def orden_nombre(valor):
    # Orden reproducible sin depender de la configuración regional del equipo.
    base = unicodedata.normalize("NFD", valor.casefold())
    return "".join(caracter for caracter in base if unicodedata.category(caracter) != "Mn")
