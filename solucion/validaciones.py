"""Reglas del enunciado, independientes de Tkinter y SQLite."""
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
