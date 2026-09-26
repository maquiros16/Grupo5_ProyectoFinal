"""Contrato de acceso a estudiantes y registros de auditoría."""
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
