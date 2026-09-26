"""Persistencia transaccional de estudiantes y auditoría en SQLite."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .contratos import Estudiante, Evento, ErrorPersistencia
from .validaciones import clave_carne, ErrorValidacion


ESQUEMA = (
    """CREATE TABLE estudiantes (
        carne TEXT NOT NULL PRIMARY KEY COLLATE CARNE_CI,
        nombre TEXT NOT NULL,
        correo TEXT NOT NULL,
        estado TEXT NOT NULL CHECK(estado IN ('activo','inactivo'))
    )""",
    """CREATE TABLE auditoria (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha_hora TEXT NOT NULL,
        accion TEXT NOT NULL CHECK(accion IN ('creacion','modificacion','cancelacion')),
        entidad TEXT NOT NULL,
        identificador TEXT NOT NULL
    )""",
)


# Compara carnés con normalización de mayúsculas y minúsculas.
def comparar_carne(primer_carne, segundo_carne):
    primero = primer_carne.casefold()
    segundo = segundo_carne.casefold()
    return (primero > segundo) - (primero < segundo)


class SesionSQLite:
    # Inicializa las dependencias y el estado del componente.
    def __init__(self, conexion):
        self.conexion = conexion

    # Busca un estudiante por carné sin distinguir capitalización.
    def obtener_estudiante(self, carne):
        fila = self.conexion.execute(
            "SELECT carne,nombre,correo,estado FROM estudiantes WHERE carne = ? COLLATE CARNE_CI",
            (carne.strip(),),
        ).fetchone()
        return Estudiante(*fila) if fila else None

    # Recupera estudiantes activos e inactivos.
    def listar_estudiantes(self):
        return [Estudiante(*fila) for fila in self.conexion.execute(
            "SELECT carne,nombre,correo,estado FROM estudiantes")]

    # Inserta un estudiante en la transacción actual.
    def insertar_estudiante(self, estudiante):
        self.conexion.execute("INSERT INTO estudiantes(carne,nombre,correo,estado) VALUES (?,?,?,?)",
                              (estudiante.carne, estudiante.nombre, estudiante.correo, estudiante.estado))

    # Actualiza los datos editables sin modificar el carné.
    def actualizar_estudiante(self, estudiante):
        cursor = self.conexion.execute(
            "UPDATE estudiantes SET nombre=?,correo=?,estado=? WHERE carne=? COLLATE CARNE_CI",
            (estudiante.nombre, estudiante.correo, estudiante.estado, estudiante.carne))
        if cursor.rowcount != 1:
            raise ErrorValidacion("Carné: el estudiante no existe.")

    # Agrega un evento a la transacción actual.
    def agregar_evento(self, fecha_hora, accion, entidad, identificador):
        self.conexion.execute(
            "INSERT INTO auditoria(fecha_hora,accion,entidad,identificador) VALUES (?,?,?,?)",
            (fecha_hora, accion, entidad, identificador))

    # Consulta los eventos desde el más reciente.
    def listar_eventos(self):
        return [Evento(*fila) for fila in self.conexion.execute(
            "SELECT id,fecha_hora,accion,entidad,identificador FROM auditoria ORDER BY id DESC")]


class PersistenciaSQLite:
    """Una conexión por aplicación, en el hilo de Tkinter.

    Inicializa solo si la BD está vacía. No migra ni altera esquemas ajenos.
    Toda escritura se confirma o revierte antes de retornar al llamador.
    """
    # Inicializa las dependencias y el estado del componente.
    def __init__(self, ruta):
        self._ocupada = False
        self._cerrada = False
        self.conexion = None
        try:
            if str(ruta) != ":memory:":
                Path(ruta).parent.mkdir(parents=True, exist_ok=True)
            self.conexion = sqlite3.connect(str(ruta), isolation_level=None, timeout=5)
            self.conexion.create_collation("CARNE_CI", comparar_carne)
            self.conexion.execute("PRAGMA foreign_keys=ON")
            tablas = {fila[0] for fila in self.conexion.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
            if not tablas:
                with self.transaccion():
                    for sentencia in ESQUEMA:
                        self.conexion.execute(sentencia)
            self._verificar_esquema()
        except (sqlite3.Error, OSError, ErrorPersistencia, ErrorValidacion) as error:
            if self.conexion is not None:
                self.conexion.close()
            raise ErrorPersistencia(
                "No se pudo abrir la base de datos con el esquema de este adaptador. "
                "Revise la ruta y las instrucciones de integración.") from error

    # Comprueba las tablas requeridas y la unicidad de los carnés.
    def _verificar_esquema(self):
        for tabla, columnas in (
            ("estudiantes", ["carne", "nombre", "correo", "estado"]),
            ("auditoria", ["id", "fecha_hora", "accion", "entidad", "identificador"]),
        ):
            # Los nombres provienen de constantes, nunca de la interfaz.
            actuales = [fila[1] for fila in self.conexion.execute(f"PRAGMA table_info({tabla})")]
            if actuales != columnas:
                raise ErrorPersistencia("Esquema incompatible; se requiere un adaptador.")
        carnes = [clave_carne(fila[0]) for fila in self.conexion.execute("SELECT carne FROM estudiantes")]
        if len(carnes) != len(set(carnes)):
            raise ErrorPersistencia("La base contiene carnés duplicados.")

    # Delimita una transacción y revierte sus cambios ante excepciones.
    @contextmanager
    def _sesion(self, escritura):
        if self._cerrada:
            raise ErrorPersistencia("La conexión ya está cerrada.")
        if self._ocupada:
            raise ErrorPersistencia("Reutilice la sesión actual; no abra transacciones anidadas.")
        self._ocupada = True
        try:
            self.conexion.execute("BEGIN IMMEDIATE" if escritura else "BEGIN")
            yield SesionSQLite(self.conexion)
            self.conexion.commit()
        except BaseException as error:
            try:
                self.conexion.rollback()
            except sqlite3.Error as error_reversion:
                raise ErrorPersistencia(
                    "No se pudo revertir la operación. Cierre la aplicación y revise la base de datos."
                ) from error_reversion
            if isinstance(error, sqlite3.Error):
                raise ErrorPersistencia(
                    "No se pudo completar la operación en la base de datos. No se guardaron los cambios.") from error
            raise
        finally:
            self._ocupada = False

    # Proporciona una sesión de escritura con confirmación o reversión.
    def transaccion(self):
        return self._sesion(True)

    # Proporciona una sesión para consultar los datos.
    def lectura(self):
        return self._sesion(False)

    # Cierra la conexión cuando no hay transacciones pendientes.
    def cerrar(self):
        if self._cerrada:
            return
        if self._ocupada or self.conexion.in_transaction:
            raise ErrorPersistencia("Hay una operación pendiente. Termine la operación antes de salir.")
        try:
            self.conexion.close()
        except sqlite3.Error as error:
            raise ErrorPersistencia("No fue posible cerrar la conexión. Intente nuevamente.") from error
        self._cerrada = True
