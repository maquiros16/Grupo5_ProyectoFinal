"""Persistencia transaccional de estudiantes, salas, reservaciones y auditoría en SQLite."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .contratos import Estudiante, Evento, Reservacion, Sala, ErrorPersistencia
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
    """CREATE TABLE salas (
        codigo TEXT NOT NULL PRIMARY KEY,
        nombre TEXT NOT NULL,
        capacidad INTEGER NOT NULL CHECK (capacidad > 0),
        estado TEXT NOT NULL CHECK (estado IN ('disponible', 'fuera_de_servicio'))
    )""",
    """CREATE TABLE reservaciones (
        identificador TEXT NOT NULL PRIMARY KEY,
        carne TEXT NOT NULL REFERENCES estudiantes(carne),
        codigo_sala TEXT NOT NULL REFERENCES salas(codigo),
        fecha TEXT NOT NULL,
        hora_inicio TEXT NOT NULL,
        duracion INTEGER NOT NULL CHECK (duracion > 0),
        cantidad_personas INTEGER NOT NULL CHECK (cantidad_personas > 0),
        estado TEXT NOT NULL
    )""",
    """CREATE TABLE secuencia_reservaciones (
        ultimo INTEGER NOT NULL
    )""",
)


ESTUDIANTES_INICIALES = (
    ("A001234567", "Andrea Solano", "andrea@universidad.ac.cr", "activo"),
    ("B009876543", "Carlos Méndez", "carlos@universidad.ac.cr", "activo"),
    ("C004567890", "Daniela Rojas", "daniela@universidad.ac.cr", "inactivo"),
)


SALAS_INICIALES = (
    ("S01", "Sala Biblioteca 1", 4, "disponible"),
    ("S02", "Sala Biblioteca 2", 6, "disponible"),
    ("S03", "Laboratorio de estudio", 10, "disponible"),
    ("S04", "Sala multimedia", 8, "fuera_de_servicio"),
    ("S05", "Cubículo individual", 1, "disponible"),
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

    # Busca una sala por su código.
    def obtener_sala(self, codigo):
        fila = self.conexion.execute(
            "SELECT codigo,nombre,capacidad,estado FROM salas WHERE codigo = ?",
            (codigo.strip(),),
        ).fetchone()
        return Sala(*fila) if fila else None

    # Recupera las salas ordenadas por código.
    def listar_salas(self):
        return [Sala(*fila) for fila in self.conexion.execute(
            "SELECT codigo,nombre,capacidad,estado FROM salas ORDER BY codigo")]

    # Inserta una sala en la transacción actual.
    def insertar_sala(self, sala):
        self.conexion.execute(
            "INSERT INTO salas(codigo,nombre,capacidad,estado) VALUES (?,?,?,?)",
            (sala.codigo, sala.nombre, sala.capacidad, sala.estado))

    # Actualiza los datos editables sin modificar el código.
    def actualizar_sala(self, sala):
        cursor = self.conexion.execute(
            "UPDATE salas SET nombre=?,capacidad=?,estado=? WHERE codigo=?",
            (sala.nombre, sala.capacidad, sala.estado, sala.codigo))
        if cursor.rowcount != 1:
            raise ErrorValidacion("Código: la sala no existe.")

    # Reserva el siguiente identificador. Cancelar una reservación no lo devuelve.
    def siguiente_identificador_reservacion(self):
        fila = self.conexion.execute("SELECT ultimo FROM secuencia_reservaciones").fetchone()
        if fila is None:
            raise ErrorPersistencia("No se pudo obtener el identificador de la reservación.")
        siguiente = fila[0] + 1
        self.conexion.execute("UPDATE secuencia_reservaciones SET ultimo=?", (siguiente,))
        return f"R{siguiente:04d}"

    # Inserta una reservación en la transacción actual.
    def insertar_reservacion(self, reservacion):
        self.conexion.execute(
            """INSERT INTO reservaciones(
                identificador,carne,codigo_sala,fecha,hora_inicio,duracion,cantidad_personas,estado)
               VALUES (?,?,?,?,?,?,?,?)""",
            (reservacion.identificador, reservacion.carne, reservacion.codigo_sala,
             reservacion.fecha, reservacion.hora_inicio, reservacion.duracion,
             reservacion.cantidad_personas, reservacion.estado))

    # Mayor cantidad de personas de una reservación activa que aún no comienza.
    def maxima_cantidad_activa_futura(self, codigo, fecha, hora):
        fila = self.conexion.execute(
            """SELECT MAX(cantidad_personas) FROM reservaciones
               WHERE codigo_sala = ? AND estado = 'activa'
               AND (fecha > ? OR (fecha = ? AND hora_inicio > ?))""",
            (codigo, fecha, fecha, hora),
        ).fetchone()
        return fila[0] or 0

    # Recupera estudiante, sala, fecha, horario, cantidad y estado dentro del rango.
    def listar_reporte(self, fecha_inicial, fecha_final):
        filas = self.conexion.execute(
            """SELECT estudiantes.nombre, salas.nombre, reservaciones.fecha,
                      reservaciones.hora_inicio, reservaciones.duracion,
                      reservaciones.cantidad_personas, reservaciones.estado
               FROM reservaciones
               JOIN estudiantes ON estudiantes.carne = reservaciones.carne
               JOIN salas ON salas.codigo = reservaciones.codigo_sala
               WHERE reservaciones.fecha >= ? AND reservaciones.fecha <= ?
               ORDER BY reservaciones.fecha, reservaciones.hora_inicio, reservaciones.identificador""",
            (fecha_inicial, fecha_final),
        ).fetchall()
        return [
            (estudiante, sala, fecha, f"{hora} ({duracion} h)", cantidad, estado)
            for estudiante, sala, fecha, hora, duracion, cantidad, estado in filas
        ]

    # Consulta los eventos desde el más reciente.
    def listar_eventos(self):
        return [Evento(*fila) for fila in self.conexion.execute(
            "SELECT id,fecha_hora,accion,entidad,identificador FROM auditoria ORDER BY id DESC")]


class PersistenciaSQLite:
    """Una conexión por aplicación, en el hilo de Tkinter.

    Inicializa solo si la BD está vacía. No migra ni altera esquemas ajenos.
    Con datos_iniciales, esa primera creación también carga los registros del enunciado.
    Toda escritura se confirma o revierte antes de retornar al llamador.
    """
    # Inicializa las dependencias y el estado del componente.
    def __init__(self, ruta, datos_iniciales=False):
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
                    self.conexion.execute("INSERT INTO secuencia_reservaciones(ultimo) VALUES (0)")
                    if datos_iniciales:
                        self._insertar_datos_iniciales()
            self._verificar_esquema()
        except (sqlite3.Error, OSError, ErrorPersistencia, ErrorValidacion) as error:
            if self.conexion is not None:
                self.conexion.close()
            raise ErrorPersistencia(
                "No se pudo abrir la base de datos con el esquema de este adaptador. "
                "Revise la ruta y las instrucciones de integración.") from error

    # Inserta los registros del enunciado durante la creación de la base.
    def _insertar_datos_iniciales(self):
        for carne, nombre, correo, estado in ESTUDIANTES_INICIALES:
            self.conexion.execute(
                "INSERT INTO estudiantes(carne,nombre,correo,estado) VALUES (?,?,?,?)",
                (carne, nombre, correo, estado))
        for codigo, nombre, capacidad, estado in SALAS_INICIALES:
            self.conexion.execute(
                "INSERT INTO salas(codigo,nombre,capacidad,estado) VALUES (?,?,?,?)",
                (codigo, nombre, capacidad, estado))

    # Comprueba las tablas requeridas y la unicidad de los carnés.
    def _verificar_esquema(self):
        for tabla, columnas in (
            ("estudiantes", ["carne", "nombre", "correo", "estado"]),
            ("auditoria", ["id", "fecha_hora", "accion", "entidad", "identificador"]),
            ("salas", ["codigo", "nombre", "capacidad", "estado"]),
            ("reservaciones", [
                "identificador", "carne", "codigo_sala", "fecha", "hora_inicio",
                "duracion", "cantidad_personas", "estado",
            ]),
            ("secuencia_reservaciones", ["ultimo"]),
        ):
            # Los nombres provienen de constantes, nunca de la interfaz.
            actuales = [fila[1] for fila in self.conexion.execute(f"PRAGMA table_info({tabla})")]
            if actuales != columnas:
                raise ErrorPersistencia("Esquema incompatible; se requiere un adaptador.")
        carnes = [clave_carne(fila[0]) for fila in self.conexion.execute("SELECT carne FROM estudiantes")]
        if len(carnes) != len(set(carnes)):
            raise ErrorPersistencia("La base contiene carnés duplicados.")
        codigos = [fila[0] for fila in self.conexion.execute("SELECT codigo FROM salas")]
        if len(codigos) != len(set(codigos)):
            raise ErrorPersistencia("La base contiene códigos de sala duplicados.")
        if self.conexion.execute("SELECT COUNT(*) FROM secuencia_reservaciones").fetchone()[0] != 1:
            raise ErrorPersistencia("Esquema incompatible; se requiere un adaptador.")

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
