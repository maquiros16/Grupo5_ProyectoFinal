"""Contrato de acceso a estudiantes, salas, reservaciones y auditoría."""
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Protocol


class ErrorPersistencia(RuntimeError):
    """Error controlado de almacenamiento."""


@dataclass(frozen=True)
class Estudiante:
    carne: str
    nombre: str
    correo: str
    estado: str = "activo"


@dataclass(frozen=True)
class Sala:
    codigo: str
    nombre: str
    capacidad: int
    estado: str = "disponible"


@dataclass(frozen=True)
class Reservacion:
    identificador: str
    carne: str
    codigo_sala: str
    fecha: str
    hora_inicio: str
    duracion: int
    cantidad_personas: int
    estado: str


@dataclass(frozen=True)
class Evento:
    id: int
    fecha_hora: str
    accion: str
    entidad: str
    identificador: str


class Sesion(Protocol):
    """Las escrituras de una sesión comparten la misma transacción."""
    # Busca un estudiante por carné sin distinguir capitalización.
    def obtener_estudiante(self, carne: str) -> Estudiante | None: ...
    # Recupera estudiantes activos e inactivos.
    def listar_estudiantes(self) -> list[Estudiante]: ...
    # Inserta un estudiante en la transacción actual.
    def insertar_estudiante(self, estudiante: Estudiante) -> None: ...
    # Actualiza los datos editables sin modificar el carné.
    def actualizar_estudiante(self, estudiante: Estudiante) -> None: ...
    # Busca una sala por su código.
    def obtener_sala(self, codigo: str) -> Sala | None: ...
    # Recupera las salas ordenadas por código.
    def listar_salas(self) -> list[Sala]: ...
    # Inserta una sala en la transacción actual.
    def insertar_sala(self, sala: Sala) -> None: ...
    # Actualiza los datos editables sin modificar el código.
    def actualizar_sala(self, sala: Sala) -> None: ...
    # Reserva el siguiente identificador R0001, R0002, sin reutilizarlo.
    def siguiente_identificador_reservacion(self) -> str: ...
    # Inserta una reservación en la transacción actual.
    def insertar_reservacion(self, reservacion: Reservacion) -> None: ...
     # Busca una reservación por su identificador.
    # Asocia una reservación existente con una serie.
    def insertar_ocurrencia_serie(
        self, id_serie: str, identificador_reservacion: str
    ) -> None: ...

    # Devuelve la serie de una reservación individual, si existe.
    def obtener_serie_de_reservacion(
        self, identificador_reservacion: str
    ) -> str | None: ...

    # Recupera las reservaciones que integran una serie.
    def listar_ocurrencias_serie(self, id_serie: str) -> list[Reservacion]: ...

    # Relaciona las reservaciones de un estudiante con sus series.
    def series_de_estudiante(self, carne: str) -> dict[str, str]: ...
    
    def obtener_reservacion(self, identificador: str) -> Reservacion | None: ...
     # Actualiza una reservación existente conservando su identificador.
    def actualizar_reservacion(self, reservacion: Reservacion) -> None: ...
    # Recupera reservaciones.
    def listar_reservaciones(self, fecha: str | None = None, codigo_sala: str | None = None,
                             estado: str | None = None,
                             carne: str | None = None) -> list[Reservacion]: ...
    # Mayor cantidad de personas de una reservación activa que aún no comienza.
    def maxima_cantidad_activa_futura(self, codigo: str, fecha: str, hora: str) -> int: ...
    # Recupera el reporte de reservaciones dentro del rango, inclusive.
    def listar_reporte(self, fecha_inicial: str, fecha_final: str) -> list[tuple]: ...
    # Agrega un evento a la transacción actual.
    def agregar_evento(self, fecha_hora: str, accion: str, entidad: str,
                      identificador: str) -> None: ...
    # Consulta los eventos desde el más reciente.
    def listar_eventos(self) -> list[Evento]: ...


class Persistencia(Protocol):
    # Proporciona una sesión de escritura con confirmación o reversión.
    def transaccion(self) -> AbstractContextManager[Sesion]: ...
    # Proporciona una sesión para consultar los datos.
    def lectura(self) -> AbstractContextManager[Sesion]: ...
    # Cierra la conexión cuando no hay transacciones pendientes.
    def cerrar(self) -> None: ...
