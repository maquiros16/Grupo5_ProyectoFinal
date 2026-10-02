"""RF-05, RF-08 y RF-15 sobre el motor de reglas. Sin SQL ni dependencias de interfaz gráfica."""
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from . import reglas
from .auditoria import Auditoria
from .contratos import Reservacion
from .estudiantes import ServicioEstudiantes
from .salas import ServicioSalas
from .validaciones import ErrorValidacion, normalizar_texto, validar_carne


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
                series_por_reserva=sesion.series_de_estudiante(estudiante.carne),
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
    
        # Recupera el historial completo, incluidas las reservaciones canceladas.
    def consultar(self):
        with self.persistencia.lectura() as sesion:
            return sesion.listar_reservaciones()

    # Busca una reservación por ID para mostrar sus datos en el formulario.
    def obtener_reservacion(self, identificador):
        identificador = normalizar_texto(identificador, "ID").upper()
        if not identificador:
            raise ErrorValidacion("ID: indique una reservación.")

        with self.persistencia.lectura() as sesion:
            reserva = sesion.obtener_reservacion(identificador)
            if reserva is None:
                raise ErrorValidacion("ID: la reservación no existe.")
            return reserva

        # Busca el historial de un estudiante sin distinguir mayúsculas y minúsculas.
    def buscar_por_estudiante(self, carne):
        carne = validar_carne(carne)
        with self.persistencia.lectura() as sesion:
            estudiante = sesion.obtener_estudiante(carne)
            if estudiante is None:
                raise ErrorValidacion("Carné: el estudiante no existe.")
            return sesion.listar_reservaciones(carne=estudiante.carne)

    # Cancela una reservación activa y registra la acción en auditoría.
    def cancelar_reservacion(self, identificador):
        identificador = normalizar_texto(identificador, "ID").upper()
        if not identificador:
            raise ErrorValidacion("ID: indique una reservación.")

        with self.persistencia.transaccion() as sesion:
            reserva = sesion.obtener_reservacion(identificador)
            if reserva is None:
                raise ErrorValidacion("ID: la reservación no existe.")
            if reserva.estado == reglas.RESERVA_CANCELADA:
                raise ErrorValidacion("La reservación ya está cancelada.")

            cancelada = replace(reserva, estado=reglas.RESERVA_CANCELADA)
            sesion.actualizar_reservacion(cancelada)
            self.auditoria.registrar(
                sesion, "cancelacion", "reservacion", identificador
            )

        return cancelada

    # Cancela las ocurrencias futuras desde la reservación seleccionada.
    def cancelar_futuras_serie(self, identificador):
        identificador = normalizar_texto(identificador, "ID").upper()
        ahora = self.reloj()

        with self.persistencia.transaccion() as sesion:
            seleccionada = sesion.obtener_reservacion(identificador)
            if seleccionada is None:
                raise ErrorValidacion("ID: la reservación no existe.")

            id_serie = sesion.obtener_serie_de_reservacion(identificador)
            if id_serie is None:
                raise ErrorValidacion("ID: la reservación no pertenece a una serie.")

            canceladas = []
            for reserva in sesion.listar_ocurrencias_serie(id_serie):
                inicio = datetime.fromisoformat(
                    f"{reserva.fecha}T{reserva.hora_inicio}"
                )
                if (
                    reserva.fecha >= seleccionada.fecha
                    and inicio > ahora
                    and reserva.estado == reglas.RESERVA_ACTIVA
                ):
                    cancelada = replace(
                        reserva, estado=reglas.RESERVA_CANCELADA
                    )
                    sesion.actualizar_reservacion(cancelada)
                    self.auditoria.registrar(
                        sesion, "cancelacion", "reservacion",
                        reserva.identificador
                    )
                    canceladas.append(cancelada)

            if not canceladas:
                raise ErrorValidacion(
                    "La serie no tiene ocurrencias futuras activas desde esa fecha."
                )

        return canceladas

    # Modifica los datos permitidos de una reservación activa conservando su ID.
    def modificar_reservacion(
        self, identificador, codigo_sala, fecha, hora_inicio, duracion, cantidad
    ):
        identificador = normalizar_texto(identificador, "ID").upper()
        if not identificador:
            raise ErrorValidacion("ID: indique una reservación.")

        ahora = self.reloj()
        with self.persistencia.transaccion() as sesion:
            reserva = sesion.obtener_reservacion(identificador)
            if reserva is None:
                raise ErrorValidacion("ID: la reservación no existe.")
            if reserva.estado != reglas.RESERVA_ACTIVA:
                raise ErrorValidacion("Solo se puede modificar una reservación activa.")

            estudiante = self.estudiantes.exigir_activo(sesion, reserva.carne)
            sala = self.salas.exigir_disponible(sesion, codigo_sala)
            horario = reglas.preparar_horario(fecha, hora_inicio, duracion, ahora)
            solicitud = reglas.validar_reservacion(
                estudiante, sala, horario.fecha, horario.hora_inicio, horario.duracion, cantidad,
                sesion.listar_reservaciones(
                    fecha=horario.fecha, codigo_sala=sala.codigo,
                    estado=reglas.RESERVA_ACTIVA,
                ),
                sesion.listar_reservaciones(
                    carne=estudiante.carne, estado=reglas.RESERVA_ACTIVA
                ),
                ahora,
                excluir_id=identificador,
                series_por_reserva=sesion.series_de_estudiante(estudiante.carne),
            )

            modificada = replace(
                reserva,
                codigo_sala=sala.codigo,
                fecha=solicitud.fecha,
                hora_inicio=solicitud.hora_inicio,
                duracion=solicitud.duracion,
                cantidad_personas=solicitud.cantidad,
            )
            sesion.actualizar_reservacion(modificada)
            self.auditoria.registrar(
                sesion, "modificacion", "reservacion", identificador
            )

        return modificada

    # Calcula las fechas semanales de una serie de 2 a 8 reservaciones.
    def fechas_recurrentes(self, fecha_inicial, semanas):
        try:
            cantidad = int(semanas)
        except (TypeError, ValueError):
            raise ErrorValidacion("Semanas: indique un número entre 2 y 8.")

        if str(semanas).strip() != str(cantidad) or not 2 <= cantidad <= 8:
            raise ErrorValidacion("Semanas: indique un número entre 2 y 8.")

        inicio = reglas.leer_fecha(fecha_inicial)
        return [
            (inicio + timedelta(weeks=indice)).isoformat()
            for indice in range(cantidad)
        ]

    # Consulta la disponibilidad de cada semana sin crear reservaciones.
    def previsualizar_recurrencia(
        self, codigo_sala, fecha_inicial, hora_inicio, duracion, semanas
    ):
        resultados = []
        for fecha in self.fechas_recurrentes(fecha_inicial, semanas):
            try:
                disponibilidad = self.consultar_disponibilidad(
                    codigo_sala, fecha, hora_inicio, duracion
                )
                conflictos = [
                    reserva.identificador
                    for reserva in disponibilidad.conflictos
                ]
                resultados.append((fecha, disponibilidad.disponible, conflictos))
            except ErrorValidacion as error:
                resultados.append((fecha, False, str(error)))
        return resultados

    # Valida todas las semanas y guarda la serie completa en una transacción.
    def crear_serie(
        self, carne, codigo_sala, fecha_inicial, hora_inicio,
        duracion, cantidad, semanas
    ):
        fechas = self.fechas_recurrentes(fecha_inicial, semanas)
        ahora = self.reloj()

        with self.persistencia.transaccion() as sesion:
            estudiante = self.estudiantes.exigir_activo(sesion, carne)
            sala = self.salas.exigir_disponible(sesion, codigo_sala)
            reservas_estudiante = sesion.listar_reservaciones(
                carne=estudiante.carne, estado=reglas.RESERVA_ACTIVA
            )
            series_por_reserva = sesion.series_de_estudiante(estudiante.carne)

            activas = reglas.contar_activas_vigentes(
                reservas_estudiante, ahora
            )
            if activas + len(fechas) > reglas.MAXIMO_RESERVAS_ACTIVAS:
                raise ErrorValidacion(
                    f"La serie agrega {len(fechas)} reservaciones "
                    f"y el estudiante ya tiene {activas} activas "
                    "presentes o futuras. El máximo permitido es "
                    f"{reglas.MAXIMO_RESERVAS_ACTIVAS}. "
                    "No se guardó ninguna ocurrencia."
                )

            solicitudes = []
            for fecha in fechas:
                try:
                    solicitud = reglas.validar_reservacion(
                        estudiante, sala, fecha, hora_inicio, duracion, cantidad,
                        sesion.listar_reservaciones(
                            fecha=fecha, codigo_sala=sala.codigo,
                            estado=reglas.RESERVA_ACTIVA,
                        ),
                        reservas_estudiante,
                        ahora,
                        series_por_reserva=series_por_reserva,
                    )
                except ErrorValidacion as error:
                    raise ErrorValidacion(
                        f"Semana {fecha}: {error}"
                    ) from error
                solicitudes.append(solicitud)

            reservaciones = []
            id_serie = None
            for solicitud in solicitudes:
                identificador = sesion.siguiente_identificador_reservacion()
                if id_serie is None:
                    id_serie = f"S{identificador[1:]}"

                reservacion = Reservacion(
                    identificador, estudiante.carne, sala.codigo,
                    solicitud.fecha, solicitud.hora_inicio,
                    solicitud.duracion, solicitud.cantidad,
                    reglas.RESERVA_ACTIVA,
                )
                sesion.insertar_reservacion(reservacion)
                sesion.insertar_ocurrencia_serie(id_serie, identificador)
                self.auditoria.registrar(
                    sesion, "creacion", "reservacion", identificador
                )
                reservaciones.append(reservacion)

        return id_serie, reservaciones
