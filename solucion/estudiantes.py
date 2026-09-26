"""RF-02, RF-03 y RF-11. Sin SQL ni dependencias de interfaz gráfica."""
from .contratos import Estudiante, Persistencia
from .auditoria import Auditoria
from .validaciones import (
    ErrorValidacion,
    orden_nombre,
    validar_carne,
    validar_correo,
    validar_estado,
    validar_nombre,
)


class ServicioEstudiantes:
    # Recibe los servicios de persistencia y auditoría de estudiantes.
    def __init__(self, persistencia: Persistencia, auditoria=None):
        self.persistencia = persistencia
        self.auditoria = auditoria or Auditoria()

    # Valida y guarda el estudiante y su evento de creación.
    def registrar(self, carne, nombre, correo):
        nuevo = Estudiante(validar_carne(carne), validar_nombre(nombre), validar_correo(correo))
        with self.persistencia.transaccion() as sesion:
            if sesion.obtener_estudiante(nuevo.carne):
                raise ErrorValidacion("Carné: ya existe un estudiante registrado con ese identificador.")
            sesion.insertar_estudiante(nuevo)
            self.auditoria.registrar(sesion, "creacion", "estudiante", nuevo.carne)
        return nuevo

    # Recupera los registros disponibles para consulta.
    def consultar(self):
        with self.persistencia.lectura() as sesion:
            return sorted(
                sesion.listar_estudiantes(),
                key=lambda estudiante: (
                    orden_nombre(estudiante.nombre),
                    estudiante.nombre.casefold(),
                    estudiante.carne.casefold(),
                ),
            )

    # Valida y guarda los cambios del estudiante junto con su auditoría.
    def modificar(self, carne, nombre, correo, estado):
        carne, nombre = validar_carne(carne), validar_nombre(nombre)
        correo, estado = validar_correo(correo), validar_estado(estado)
        with self.persistencia.transaccion() as sesion:
            actual = sesion.obtener_estudiante(carne)
            if actual is None:
                raise ErrorValidacion("Carné: el estudiante no existe.")
            nuevo = Estudiante(actual.carne, nombre, correo, estado)
            if nuevo != actual:
                sesion.actualizar_estudiante(nuevo)
                self.auditoria.registrar(sesion, "modificacion", "estudiante", actual.carne)
        return nuevo

    # Rechaza estudiantes inexistentes o inactivos antes de reservar.
    def exigir_activo(self, sesion, carne):
        """Comprueba RN-01 dentro de la transacción de reservación."""
        estudiante = sesion.obtener_estudiante(validar_carne(carne))
        if estudiante is None:
            raise ErrorValidacion("Carné: el estudiante no existe.")
        if estudiante.estado != "activo":
            raise ErrorValidacion("El estudiante está inactivo y no puede crear nuevas reservaciones.")
        return estudiante
