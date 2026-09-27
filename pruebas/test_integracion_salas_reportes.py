import csv
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from solucion.auditoria import Auditoria
from solucion.contratos import ErrorPersistencia, Estudiante, Reservacion
from solucion.persistencia import ESTUDIANTES_INICIALES, PersistenciaSQLite, SALAS_INICIALES
from solucion.reportes import ServicioReportes, exportar_csv
from solucion.salas import ServicioSalas
from solucion.validaciones import ErrorValidacion


class SalasReportesTest(unittest.TestCase):
    # Prepara una base vacía, sin los registros iniciales de la aplicación.
    def setUp(self):
        self.directorio = tempfile.TemporaryDirectory()
        self.ruta = Path(self.directorio.name) / "test.sqlite3"
        self.persistencia = PersistenciaSQLite(self.ruta)
        self.reloj = lambda: datetime(2026, 9, 27, 10, 0, tzinfo=timezone.utc)
        self.auditoria = Auditoria(self.reloj)
        self.salas = ServicioSalas(self.persistencia, self.auditoria, self.reloj)
        self.reportes = ServicioReportes(self.persistencia)

    # Libera la base temporal.
    def tearDown(self):
        self.persistencia.cerrar()
        self.directorio.cleanup()

    # Registra una sala de prueba.
    def alta(self, codigo="S06", capacidad="4"):
        return self.salas.registrar(codigo, "Sala de prueba", capacidad)

    # Inserta una reservación con el identificador que sigue en la secuencia.
    def reservar(self, codigo, fecha, hora, cantidad, estado="activa", carne="A001234567"):
        with self.persistencia.transaccion() as sesion:
            if sesion.obtener_estudiante(carne) is None:
                sesion.insertar_estudiante(Estudiante(
                    carne, "Carlos Méndez", "carlos@universidad.ac.cr", "activo",
                ))
            identificador = sesion.siguiente_identificador_reservacion()
            sesion.insertar_reservacion(Reservacion(
                identificador, carne, codigo, fecha, hora, 1, cantidad, estado,
            ))
        return identificador

    # Carga los datos del enunciado una sola vez.
    def test_rf01_datos_iniciales_sin_duplicar(self):
        self.persistencia.cerrar()
        self.persistencia = PersistenciaSQLite(self.ruta.parent / "inicial.sqlite3", datos_iniciales=True)
        with self.persistencia.lectura() as sesion:
            estudiantes = sesion.listar_estudiantes()
            salas = sesion.listar_salas()
        self.assertEqual(
            sorted((estudiante.carne, estudiante.nombre, estudiante.estado) for estudiante in estudiantes),
            sorted((carne, nombre, estado) for carne, nombre, _correo, estado in ESTUDIANTES_INICIALES),
        )
        self.assertEqual(
            [(sala.codigo, sala.nombre, sala.capacidad, sala.estado) for sala in salas],
            list(SALAS_INICIALES),
        )
        self.assertEqual(salas[3].estado, "fuera_de_servicio")
        self.persistencia.cerrar()
        self.persistencia = PersistenciaSQLite(self.ruta.parent / "inicial.sqlite3", datos_iniciales=True)
        self.assertEqual(len(ServicioSalas(self.persistencia).consultar()), len(SALAS_INICIALES))

    # La consulta incluye las salas fuera de servicio y las ordena por código.
    def test_rf04_consulta_ordenada_incluye_fuera_de_servicio(self):
        self.assertEqual(self.salas.consultar(), [])
        self.alta("S10")
        self.salas.registrar("S02", "Biblioteca", "6", "fuera_de_servicio")
        self.assertEqual([sala.codigo for sala in self.salas.consultar()], ["S02", "S10"])
        self.assertEqual(self.salas.consultar()[0].estado, "fuera_de_servicio")

    # El código no cambia y la auditoría registra creación y modificación.
    def test_rf12_registro_y_modificacion(self):
        sala = self.alta()
        modificada = self.salas.modificar("S06", "Sala nueva", "5", "fuera_de_servicio")
        self.assertEqual(modificada.codigo, sala.codigo)
        with self.persistencia.transaccion() as sesion:
            with self.assertRaisesRegex(ErrorValidacion, "fuera de servicio"):
                self.salas.exigir_disponible(sesion, "S06")
        self.salas.modificar(sala.codigo, sala.nombre, "4", "disponible")
        self.assertEqual(
            [evento.accion for evento in self.auditoria.consultar(self.persistencia)],
            ["modificacion", "modificacion", "creacion"],
        )

    # Rechaza duplicados, datos inválidos y bajar la capacidad bajo una reservación futura.
    def test_rf12_rechazos(self):
        self.alta()
        with self.assertRaisesRegex(ErrorValidacion, "Código"):
            self.alta()
        with self.assertRaises(ErrorValidacion):
            self.salas.registrar("S07", "AB", "0")
        self.reservar("S06", "2026-09-28", "08:00", 3)
        with self.assertRaisesRegex(ErrorValidacion, "Capacidad"):
            self.salas.modificar("S06", "Sala de prueba", "2", "disponible")
        self.assertEqual(self.salas.consultar()[0].capacidad, 4)
        self.salas.modificar("S06", "Sala de prueba", "3", "disponible")
        self.assertEqual(self.salas.consultar()[0].capacidad, 3)

    # Una reservación pasada o cancelada no impide reducir la capacidad.
    def test_rf12_capacidad_ignora_pasadas_y_canceladas(self):
        self.alta()
        self.reservar("S06", "2026-09-27", "09:00", 4)
        self.reservar("S06", "2026-09-28", "08:00", 4, estado="cancelada")
        self.salas.modificar("S06", "Sala de prueba", "1", "disponible")
        self.assertEqual(self.salas.consultar()[0].capacidad, 1)

    # El identificador avanza y no se reutiliza aunque la transacción se revierta.
    def test_rf01_identificadores_sin_reutilizar(self):
        with self.persistencia.transaccion() as sesion:
            self.assertEqual(sesion.siguiente_identificador_reservacion(), "R0001")
        with self.assertRaises(RuntimeError):
            with self.persistencia.transaccion() as sesion:
                sesion.siguiente_identificador_reservacion()
                raise RuntimeError("revertir")
        with self.persistencia.transaccion() as sesion:
            self.assertEqual(sesion.siguiente_identificador_reservacion(), "R0002")
        self.persistencia.cerrar()
        self.persistencia = PersistenciaSQLite(self.ruta)
        with self.persistencia.transaccion() as sesion:
            self.assertEqual(sesion.siguiente_identificador_reservacion(), "R0003")

    # El reporte exige el rango, lo consulta y lo exporta en UTF-8 aparte de la consulta.
    def test_rf16_rango_consulta_y_csv(self):
        with self.assertRaises(ErrorValidacion):
            self.reportes.generar("", "2026-09-28")
        with self.assertRaisesRegex(ErrorValidacion, "anterior"):
            self.reportes.generar("2026-09-28", "2026-09-27")
        self.alta("S06")
        with self.persistencia.transaccion() as sesion:
            sesion.insertar_estudiante(self._estudiante())
            identificador = sesion.siguiente_identificador_reservacion()
            sesion.insertar_reservacion(Reservacion(
                identificador, "A001234567", "S06", "2026-09-28", "08:00", 2, 3, "activa",
            ))
            sesion.insertar_reservacion(Reservacion(
                sesion.siguiente_identificador_reservacion(), "A001234567", "S06",
                "2026-10-01", "08:00", 1, 1, "activa",
            ))
        filas = self.reportes.generar("2026-09-28", "2026-09-28")
        self.assertEqual(filas, [(
            "Carlos Méndez", "Sala de prueba", "2026-09-28", "08:00 (2 h)", 3, "activa",
        )])
        destino = self.ruta.parent / "reporte.csv"
        exportar_csv(filas, destino)
        with destino.open(encoding="utf-8", newline="") as archivo:
            contenido = list(csv.reader(archivo))
        self.assertEqual(contenido[0][0], "Estudiante")
        self.assertIn("Méndez", contenido[1][0])

    # Arma el estudiante usado por el reporte.
    @staticmethod
    def _estudiante():
        return Estudiante("A001234567", "Carlos Méndez", "carlos@universidad.ac.cr", "activo")

    # Una reservación no puede apuntar a un estudiante o una sala inexistentes.
    def test_rf01_integridad_referencial(self):
        self.alta()
        with self.assertRaises(ErrorPersistencia):
            with self.persistencia.transaccion() as sesion:
                sesion.insertar_reservacion(Reservacion(
                    "R0001", "A001234567", "S06", "2026-09-28", "08:00", 1, 1, "activa",
                ))
