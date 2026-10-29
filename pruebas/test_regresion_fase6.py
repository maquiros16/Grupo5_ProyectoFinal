"""Regresión de la Fase 6: defectos BUG-02 a BUG-05 y BUG-07 corregidos.

Pruebas sin interfaz gráfica (RNF-10). BUG-01 y BUG-06 se verifican en
pruebas.test_fase5_salas_persistencia_reportes (CP-RF04-04 y CP-RF16-04).
Ejecución: python -m unittest pruebas.test_regresion_fase6 -v
"""
import csv
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from solucion.auditoria import Auditoria
from solucion.contratos import Estudiante, Reservacion
from solucion.persistencia import PersistenciaSQLite
from solucion.reglas import validar_hora
from solucion.reportes import ENCABEZADOS_CSV, ServicioReportes, exportar_csv
from solucion.salas import ServicioSalas
from solucion.validaciones import (
    CAPACIDAD_MAXIMA, ErrorValidacion, validar_capacidad, validar_rango_fechas,
)


class RegresionValidacionesTest(unittest.TestCase):

    # BUG-02: una capacidad enorme se rechaza con un mensaje sobre la capacidad.
    def test_bug02_capacidad_muy_grande(self):
        for valor in ("1000000000000000000000000000000", str(CAPACIDAD_MAXIMA + 1)):
            with self.subTest(valor=valor):
                with self.assertRaisesRegex(ErrorValidacion, "^Capacidad: el número indicado es demasiado grande"):
                    validar_capacidad(valor)
        self.assertEqual(validar_capacidad(str(CAPACIDAD_MAXIMA)), CAPACIDAD_MAXIMA)
        self.assertEqual(validar_capacidad(" 1 "), 1)

    # BUG-02: dígitos que no son ASCII no se aceptan como capacidad.
    def test_bug02_digitos_no_ascii(self):
        for valor in ("²", "٣", "-1", "0", "2.5", ""):
            with self.subTest(valor=valor), self.assertRaisesRegex(ErrorValidacion, "^Capacidad:"):
                validar_capacidad(valor)

    # BUG-04: una fecha vacía pide ingresarla; los demás mensajes se conservan.
    def test_bug04_fecha_vacia_pide_ingresarla(self):
        with self.assertRaisesRegex(ErrorValidacion, "^Fecha inicial: ingrese la fecha, es obligatoria"):
            validar_rango_fechas("", "2026-12-31")
        with self.assertRaisesRegex(ErrorValidacion, "^Fecha final: ingrese la fecha, es obligatoria"):
            validar_rango_fechas("2026-12-01", "   ")
        with self.assertRaisesRegex(ErrorValidacion, "AAAA-MM-DD"):
            validar_rango_fechas("abc", "2026-12-31")
        with self.assertRaisesRegex(ErrorValidacion, "anterior"):
            validar_rango_fechas("2026-12-20", "2026-12-10")

    # BUG-07: la hora vacía indica que falta; el formato inválido conserva su mensaje.
    def test_bug07_hora_vacia_indica_que_falta(self):
        for valor in ("", "   "):
            with self.subTest(valor=valor):
                with self.assertRaisesRegex(ErrorValidacion, "^Hora de inicio: indique la hora de inicio, es obligatoria"):
                    validar_hora(valor)
        with self.assertRaisesRegex(ErrorValidacion, "HH:MM"):
            validar_hora("9")
        self.assertEqual(validar_hora("09:00"), 9)


class RegresionSalasReportesTest(unittest.TestCase):

    def setUp(self):
        self.directorio = tempfile.TemporaryDirectory()
        self.ruta = Path(self.directorio.name) / "regresion.sqlite3"
        self.persistencia = PersistenciaSQLite(self.ruta)
        reloj = lambda: datetime(2026, 10, 29, 10, 0, tzinfo=timezone.utc)
        self.salas = ServicioSalas(self.persistencia, Auditoria(reloj), reloj)
        self.reportes = ServicioReportes(self.persistencia)
        # La base de prueba se crea vacía: se registran los datos que usa cada caso.
        self.salas.registrar("S01", "Sala Biblioteca 1", "4")
        self.salas.registrar("S03", "Laboratorio de estudio", "10")
        with self.persistencia.transaccion() as sesion:
            sesion.insertar_estudiante(Estudiante(
                "A001234567", "Andrea Solano", "andrea@universidad.ac.cr", "activo"))
        self.persistencia.conexion.execute("DELETE FROM auditoria")
        self.persistencia.conexion.commit()

    def tearDown(self):
        self.persistencia.cerrar()
        self.directorio.cleanup()

    # BUG-03: el código de sala es único sin distinguir mayúsculas y minúsculas.
    def test_bug03_codigo_repetido_con_otra_capitalizacion(self):
        antes = self.salas.consultar()
        for codigo in ("s01", "S01", " s01 "):
            with self.subTest(codigo=codigo):
                with self.assertRaisesRegex(ErrorValidacion, "^Código: ya existe"):
                    self.salas.registrar(codigo, "Sala Copia", "3")
        self.assertEqual(self.salas.consultar(), antes)
        eventos = self.persistencia.conexion.execute(
            "SELECT COUNT(*) FROM auditoria WHERE entidad = 'sala'").fetchone()[0]
        self.assertEqual(eventos, 0, "Un rechazo no debe registrarse en la auditoría")
        self.assertEqual(self.salas.registrar("s06", "Sala nueva", "3").codigo, "s06")

    # BUG-05: el CSV incluye el carné y el horario con hora de inicio y de fin.
    def test_bug05_csv_con_carne_y_hora_de_fin(self):
        with self.persistencia.transaccion() as sesion:
            for hora, duracion in (("09:00", 2), ("18:00", 2), ("08:00", 1)):
                sesion.insertar_reservacion(Reservacion(
                    sesion.siguiente_identificador_reservacion(), "A001234567", "S03",
                    "2026-12-15", hora, duracion, 2, "activa",
                ))
        filas = self.reportes.generar("2026-12-15", "2026-12-15")
        destino = Path(self.directorio.name) / "reporte.csv"
        exportar_csv(filas, destino)
        with destino.open(encoding="utf-8", newline="") as archivo:
            contenido = list(csv.reader(archivo))
        self.assertEqual(contenido[0], list(ENCABEZADOS_CSV))
        self.assertEqual([fila[0] for fila in contenido[1:]], ["A001234567"] * 3)
        self.assertEqual([fila[4] for fila in contenido[1:]], ["08:00-09:00", "09:00-11:00", "18:00-20:00"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
