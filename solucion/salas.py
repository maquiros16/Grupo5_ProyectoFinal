"""RF-04 y RF-12. Sin SQL ni dependencias de interfaz gráfica."""
from datetime import datetime

from .auditoria import Auditoria
from .contratos import Persistencia, Sala
from .validaciones import (
    ErrorValidacion,
    validar_capacidad,
    validar_codigo_sala,
    validar_estado_sala,
    validar_nombre,
)


class ServicioSalas:
    # Recibe los servicios de persistencia y auditoría de salas.
    def __init__(self, persistencia: Persistencia, auditoria=None, reloj=None):
        self.persistencia = persistencia
        self.auditoria = auditoria or Auditoria()
        self.reloj = reloj or (lambda: datetime.now().astimezone())

    # Valida y guarda la sala y su evento de creación.
    def registrar(self, codigo, nombre, capacidad, estado="disponible"):
        nueva = Sala(
            validar_codigo_sala(codigo), validar_nombre(nombre),
            validar_capacidad(capacidad), validar_estado_sala(estado),
        )
        with self.persistencia.transaccion() as sesion:
            if sesion.obtener_sala(nueva.codigo):
                raise ErrorValidacion("Código: ya existe una sala registrada con ese identificador.")
            sesion.insertar_sala(nueva)
            self.auditoria.registrar(sesion, "creacion", "sala", nueva.codigo)
        return nueva

    # Recupera las salas disponibles y fuera de servicio, ordenadas por código.
    def consultar(self):
        with self.persistencia.lectura() as sesion:
            return sesion.listar_salas()

    # Valida y guarda los cambios de la sala junto con su auditoría.
    def modificar(self, codigo, nombre, capacidad, estado):
        codigo, nombre = validar_codigo_sala(codigo), validar_nombre(nombre)
        capacidad, estado = validar_capacidad(capacidad), validar_estado_sala(estado)
        with self.persistencia.transaccion() as sesion:
            actual = sesion.obtener_sala(codigo)
            if actual is None:
                raise ErrorValidacion("Código: la sala no existe.")
            nueva = Sala(actual.codigo, nombre, capacidad, estado)
            if nueva != actual:
                if capacidad < actual.capacidad:
                    ahora = self.reloj()
                    ocupacion = sesion.maxima_cantidad_activa_futura(
                        actual.codigo, ahora.date().isoformat(), ahora.strftime("%H:%M"))
                    if capacidad < ocupacion:
                        raise ErrorValidacion(
                            "Capacidad: no puede ser menor que la cantidad de personas "
                            "de una reservación activa futura de esta sala.")
                sesion.actualizar_sala(nueva)
                self.auditoria.registrar(sesion, "modificacion", "sala", actual.codigo)
        return nueva

    # Rechaza salas inexistentes o fuera de servicio antes de reservar.
    def exigir_disponible(self, sesion, codigo):
        """Comprueba la disponibilidad dentro de la transacción de reservación."""
        sala = sesion.obtener_sala(validar_codigo_sala(codigo))
        if sala is None:
            raise ErrorValidacion("Código: la sala no existe.")
        if sala.estado != "disponible":
            raise ErrorValidacion("La sala está fuera de servicio y no puede usarse para nuevas reservaciones.")
        return sala
