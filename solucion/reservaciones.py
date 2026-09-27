"""RF-05, RF-08 y RF-15 sobre el motor de reglas. Sin SQL ni dependencias de interfaz gráfica."""
from dataclasses import dataclass
from datetime import datetime

from . import reglas
from .auditoria import Auditoria
from .contratos import Reservacion
from .estudiantes import ServicioEstudiantes
from .salas import ServicioSalas
from .validaciones import ErrorValidacion, normalizar_texto


ESTADOS_RESERVA = (reglas.RESERVA_ACTIVA, reglas.RESERVA_CANCELADA)
HORAS_DE_USO = reglas.HORA_CIERRE - reglas.HORA_APERTURA


@dataclass(frozen=True)
class OcupacionSala:
    codigo: str
    nombre: str
    estado: str
    horas_reservadas: int

    # Calcula el porcentaje de horas reservadas sobre el horario de uso.
    @property
    def porcentaje(self):
        return round(self.horas_reservadas * 100 / HORAS_DE_USO)


@dataclass(frozen=True)
class Panel:
    fecha_ocupacion: str
    hoy: list
    proximas: list
    ocupacion: list
    filtradas: list


# Ordena reservaciones por fecha y luego por hora de inicio.
def ordenar(reservas):
    return sorted(reservas, key=lambda reserva: (reserva.fecha, reserva.hora_inicio, reserva.identificador))


class ServicioReservaciones:
    # Recibe la persistencia, la auditoría y el reloj usado por las reglas.
    def __init__(self, persistencia, auditoria=None, reloj=None):
        self.persistencia = persistencia
        self.auditoria = auditoria or Auditoria()
        self.reloj = reloj or datetime.now
        # Reutiliza las validaciones de estudiante activo y sala disponible.
        self.estudiantes = ServicioEstudiantes(persistencia, self.auditoria)
        self.salas = ServicioSalas(persistencia, self.auditoria)

    # Recupera las salas ordenadas por código para los formularios.
    def listar_salas(self):
        with self.persistencia.lectura() as sesion:
            return sesion.listar_salas()

    # Valida todas las reglas y guarda la reservación con su auditoría.
    def crear(self, carne, codigo_sala, fecha, hora_inicio, duracion, cantidad):
        ahora = self.reloj()
        with self.persistencia.transaccion() as sesion:
            estudiante = self.estudiantes.exigir_activo(sesion, carne)
            sala = self.salas.exigir_disponible(sesion, codigo_sala)
            horario = reglas.preparar_horario(fecha, hora_inicio, duracion, ahora)
            solicitud = reglas.validar_reservacion(
                estudiante, sala, horario.fecha, horario.hora_inicio, horario.duracion, cantidad,
                sesion.listar_reservaciones(
                    fecha=horario.fecha, codigo_sala=sala.codigo, estado=reglas.RESERVA_ACTIVA),
                sesion.listar_reservaciones(carne=estudiante.carne, estado=reglas.RESERVA_ACTIVA),
                ahora,
            )
            reservacion = Reservacion(
                sesion.siguiente_identificador_reservacion(), estudiante.carne, sala.codigo,
                solicitud.fecha, solicitud.hora_inicio, solicitud.duracion, solicitud.cantidad,
                reglas.RESERVA_ACTIVA,
            )
            sesion.insertar_reservacion(reservacion)
            self.auditoria.registrar(sesion, "creacion", "reservacion", reservacion.identificador)
        return reservacion

    # Consulta si un horario está libre sin crear ni modificar datos.
    def consultar_disponibilidad(self, codigo_sala, fecha, hora_inicio, duracion):
        ahora = self.reloj()
        with self.persistencia.lectura() as sesion:
            sala = self.salas.exigir_disponible(sesion, codigo_sala)
            horario = reglas.preparar_horario(fecha, hora_inicio, duracion, ahora)
            return reglas.evaluar_disponibilidad(
                sala, horario.fecha, horario.hora_inicio, horario.duracion,
                sesion.listar_reservaciones(
                    fecha=horario.fecha, codigo_sala=sala.codigo, estado=reglas.RESERVA_ACTIVA),
                ahora,
            )

    # Reúne las reservas de hoy, las próximas, la ocupación por sala y los resultados filtrados.
    def panel(self, fecha=None, codigo_sala=None, estado=None):
        ahora = self.reloj()
        hoy = ahora.date().isoformat()
        fecha = reglas.leer_fecha(fecha).isoformat() if fecha else None
        codigo_sala = normalizar_texto(codigo_sala, "Sala") if codigo_sala else None
        estado = normalizar_texto(estado, "Estado") if estado else None
        if estado and estado not in ESTADOS_RESERVA:
            raise ErrorValidacion("Estado: seleccione activa o cancelada.")
        fecha_ocupacion = fecha or hoy
        with self.persistencia.lectura() as sesion:
            if codigo_sala and sesion.obtener_sala(codigo_sala) is None:
                raise ErrorValidacion("Sala: la sala no existe.")
            salas = sesion.listar_salas()
            activas = ordenar(sesion.listar_reservaciones(estado=reglas.RESERVA_ACTIVA))
            filtradas = ordenar(sesion.listar_reservaciones(
                fecha=fecha, codigo_sala=codigo_sala, estado=estado))
        horas = {}
        for reserva in activas:
            if reserva.fecha == fecha_ocupacion:
                horas[reserva.codigo_sala] = horas.get(reserva.codigo_sala, 0) + reserva.duracion
        return Panel(
            fecha_ocupacion,
            [reserva for reserva in activas if reserva.fecha == hoy],
            [reserva for reserva in activas
             if datetime.fromisoformat(f"{reserva.fecha}T{reserva.hora_inicio}") > ahora],
            [OcupacionSala(sala.codigo, sala.nombre, sala.estado, horas.get(sala.codigo, 0)) for sala in salas],
            filtradas,
        )
