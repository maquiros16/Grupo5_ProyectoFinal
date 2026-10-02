"""Motor de reglas de reservación:

Funciones puras: 
- Reciben los datos ya consultados y la fecha/hora actual, no usan SQLite ni Tkinter. 
- Cada regla rechaza con ErrorValidacion y un mensaje que puede mostrarse directamente a la persona usuaria.

Uso desde otros módulos (creación, modificación y recurrencia):
    solicitud = validar_reservacion(estudiante, sala, fecha, hora_inicio,
                                    duracion, cantidad, reservas_sala,
                                    reservas_estudiante, ahora, excluir_id)

Para modificar una reservación se envía su identificador en excluir_id, así
no choca consigo misma ni cuenta dos veces en el límite por estudiante.
"""
import re
from dataclasses import dataclass
from datetime import date, datetime, time

from .validaciones import ErrorValidacion, normalizar_texto


SALA_DISPONIBLE = "disponible"
SALA_FUERA_DE_SERVICIO = "fuera_de_servicio"
RESERVA_ACTIVA = "activa"
RESERVA_CANCELADA = "cancelada"
HORA_APERTURA = 8
HORA_CIERRE = 20
DURACIONES_PERMITIDAS = (1, 2)
MAXIMO_RESERVAS_ACTIVAS = 3

_FORMATO_FECHA = re.compile(r"\d{4}-\d{2}-\d{2}")
_FORMATO_HORA = re.compile(r"\d{2}:\d{2}")
_ENTERO = re.compile(r"[+-]?\d+")


@dataclass(frozen=True)
class Horario:
    fecha: str        # AAAA-MM-DD
    hora_inicio: str  # HH:MM
    hora_fin: str     # HH:MM
    duracion: int


@dataclass(frozen=True)
class Solicitud:
    fecha: str
    hora_inicio: str
    hora_fin: str
    duracion: int
    cantidad: int


@dataclass(frozen=True)
class ResultadoDisponibilidad:
    horario: Horario
    conflictos: tuple

    # Indica si el horario no tiene conflictos activos.
    @property
    def disponible(self):
        return not self.conflictos


# Convierte un texto o entero en un número entero sin aceptar decimales.
def leer_entero(valor, campo):
    if isinstance(valor, bool):
        raise ErrorValidacion(f"{campo}: debe ser un número entero.")
    if isinstance(valor, int):
        return valor
    if isinstance(valor, str) and _ENTERO.fullmatch(valor.strip()):
        return int(valor.strip())
    raise ErrorValidacion(f"{campo}: debe ser un número entero.")


# Convierte una hora HH:MM en minutos desde la medianoche.
def a_minutos(hora):
    horas, minutos = hora.split(":")
    return int(horas) * 60 + int(minutos)


# Da formato HH:MM a una hora completa.
def formato_hora(hora):
    return f"{hora:02d}:00"


# Calcula la hora de finalización de una reservación guardada.
def hora_fin(reserva):
    minutos = a_minutos(reserva.hora_inicio) + reserva.duracion * 60
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


# Rechaza estudiantes inexistentes o inactivos.
def validar_estudiante(estudiante):
    if estudiante is None:
        raise ErrorValidacion("Carné: el estudiante no existe.")
    if estudiante.estado != "activo":
        raise ErrorValidacion("El estudiante está inactivo y no puede crear nuevas reservaciones.")
    return estudiante


# Valida el formato de la fecha y que no sea anterior a hoy.
def validar_fecha(valor, hoy):
    fecha = leer_fecha(valor)
    if fecha < hoy:
        raise ErrorValidacion("Fecha: no puede ser anterior a la fecha actual.")
    return fecha


# Revisa solo el formato de la fecha, también para los filtros de consulta.
def leer_fecha(valor):
    valor = normalizar_texto(valor, "Fecha")
    if not _FORMATO_FECHA.fullmatch(valor):
        raise ErrorValidacion("Fecha: use el formato AAAA-MM-DD.")
    try:
        return date.fromisoformat(valor)
    except ValueError:
        raise ErrorValidacion("Fecha: la fecha indicada no existe.") from None


# Valida el formato de 24 horas y que la hora sea completa.
def validar_hora(valor):
    valor = normalizar_texto(valor, "Hora de inicio")
    if not _FORMATO_HORA.fullmatch(valor):
        raise ErrorValidacion("Hora de inicio: use el formato de 24 horas HH:MM.")
    horas, minutos = int(valor[:2]), int(valor[3:])
    if horas > 23 or minutos > 59:
        raise ErrorValidacion("Hora de inicio: la hora indicada no existe.")
    if minutos != 0:
        raise ErrorValidacion("Hora de inicio: debe comenzar en una hora completa (por ejemplo 09:00).")
    return horas


# Comprueba que la duración sea de 1 o 2 horas.
def validar_duracion(valor):
    duracion = leer_entero(valor, "Duración")
    if duracion not in DURACIONES_PERMITIDAS:
        raise ErrorValidacion("Duración: solo se permiten reservas de 1 o 2 horas.")
    return duracion


# Comprueba que la reserva quede dentro del horario de 08:00 a 20:00.
def validar_horario(hora, duracion):
    if hora < HORA_APERTURA:
        raise ErrorValidacion("Hora de inicio: el horario de uso inicia a las 08:00.")
    if hora + duracion > HORA_CIERRE:
        raise ErrorValidacion("Horario: ninguna reserva puede terminar después de las 20:00.")


# Rechaza reservas de hoy que no inicien después de la hora actual.
def validar_inicio_futuro(fecha, hora, ahora):
    if fecha == ahora.date() and datetime.combine(fecha, time(hora)) <= ahora:
        raise ErrorValidacion("Hora de inicio: para hoy, la reserva debe iniciar después de la hora actual.")


# Valida que la cantidad sea entera, mayor que cero y no supere la capacidad.
def validar_cantidad(valor, capacidad):
    cantidad = leer_entero(valor, "Cantidad de personas")
    if cantidad <= 0:
        raise ErrorValidacion("Cantidad de personas: debe ser mayor que cero.")
    if cantidad > capacidad:
        raise ErrorValidacion(f"Cantidad de personas: supera la capacidad de la sala ({capacidad}).")
    return cantidad


# Rechaza salas inexistentes o fuera de servicio.
def validar_sala(sala):
    if sala is None:
        raise ErrorValidacion("Sala: la sala no existe.")
    if sala.estado != SALA_DISPONIBLE:
        raise ErrorValidacion("Sala: está fuera de servicio y no puede reservarse.")
    return sala


# Valida fecha, hora y duración y devuelve el horario normalizado.
def preparar_horario(fecha, hora_inicio, duracion, ahora):
    fecha = validar_fecha(fecha, ahora.date())
    hora = validar_hora(hora_inicio)
    duracion = validar_duracion(duracion)
    validar_horario(hora, duracion)
    validar_inicio_futuro(fecha, hora, ahora)
    return Horario(fecha.isoformat(), formato_hora(hora), formato_hora(hora + duracion), duracion)


# Indica si dos horarios se superponen según el criterio del enunciado.
def hay_superposicion(inicio_nuevo, fin_nuevo, inicio_existente, fin_existente):
    return (a_minutos(inicio_nuevo) < a_minutos(fin_existente)
            and a_minutos(fin_nuevo) > a_minutos(inicio_existente))


# Busca las reservas activas de la misma sala y fecha que chocan con el horario.
def buscar_conflictos(codigo_sala, horario, reservas, excluir_id=None):
    return tuple(
        reserva for reserva in reservas
        if reserva.estado == RESERVA_ACTIVA
        and reserva.identificador != excluir_id
        and reserva.codigo_sala == codigo_sala
        and reserva.fecha == horario.fecha
        and hay_superposicion(horario.hora_inicio, horario.hora_fin, reserva.hora_inicio, hora_fin(reserva))
    )


# Rechaza el horario si choca con una reserva activa.
def validar_sin_conflictos(codigo_sala, horario, reservas, excluir_id=None):
    conflictos = buscar_conflictos(codigo_sala, horario, reservas, excluir_id)
    if conflictos:
        detalle = ", ".join(
            f"{reserva.identificador} ({reserva.hora_inicio}-{hora_fin(reserva)})" for reserva in conflictos
        )
        raise ErrorValidacion(f"La sala ya está reservada en ese horario: {detalle}.")


# Cuenta cada reservación activa presente o futura por separado.
def contar_activas_vigentes(
    reservas_estudiante, ahora, excluir_id=None, series_por_reserva=None
):
    return sum(
        1
        for reserva in reservas_estudiante
        if reserva.estado == RESERVA_ACTIVA
        and reserva.identificador != excluir_id
        and datetime.fromisoformat(
            f"{reserva.fecha}T{hora_fin(reserva)}"
        ) > ahora
    )


# Rechaza una nueva reserva cuando el estudiante ya tiene tres activas.
def validar_limite_estudiante(
    reservas_estudiante, ahora, excluir_id=None, series_por_reserva=None
):
    cantidad = contar_activas_vigentes(
        reservas_estudiante, ahora, excluir_id, series_por_reserva
    )
    if cantidad >= MAXIMO_RESERVAS_ACTIVAS:
        raise ErrorValidacion(
            f"El estudiante ya tiene {MAXIMO_RESERVAS_ACTIVAS} "
            "reservaciones activas presentes o futuras."
        )


# Ejecuta todas las reglas de creación o modificación en un orden fijo.
def validar_reservacion(estudiante, sala, fecha, hora_inicio, duracion, cantidad,
                        reservas_sala, reservas_estudiante, ahora, excluir_id=None,
                        series_por_reserva=None):
    validar_estudiante(estudiante)
    validar_sala(sala)
    horario = preparar_horario(fecha, hora_inicio, duracion, ahora)
    cantidad = validar_cantidad(cantidad, sala.capacidad)
    validar_limite_estudiante(
        reservas_estudiante, ahora, excluir_id, series_por_reserva
    )
    validar_sin_conflictos(sala.codigo, horario, reservas_sala, excluir_id)
    return Solicitud(horario.fecha, horario.hora_inicio, horario.hora_fin, horario.duracion, cantidad)


# Evalúa si un horario está libre sin crear ninguna reserva.
def evaluar_disponibilidad(sala, fecha, hora_inicio, duracion, reservas_sala, ahora):
    validar_sala(sala)
    horario = preparar_horario(fecha, hora_inicio, duracion, ahora)
    return ResultadoDisponibilidad(horario, buscar_conflictos(sala.codigo, horario, reservas_sala))
