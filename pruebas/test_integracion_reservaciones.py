"""Pruebas de RF-05, RF-08 y RF-15 con SQLite real y con widgets reales."""
import tempfile
import tkinter as tk
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from solucion.auditoria import Auditoria
from solucion.contratos import ErrorPersistencia
from solucion.estudiantes import ServicioEstudiantes
from solucion.persistencia import PersistenciaSQLite
from solucion.reservaciones import ServicioReservaciones
from solucion.validaciones import ErrorValidacion


AHORA = datetime(2026, 9, 28, 10, 30)
ACTIVO = "A001234567"      # Estudiante activo de los datos iniciales.
INACTIVO = "C004567890"    # Estudiante inactivo de los datos iniciales.
OTRO_ACTIVO = "B009876543"


class ServicioReservacionesTest(unittest.TestCase):
    # Prepara una base temporal con los datos iniciales y el reloj fijo.
    def setUp(self):
        self.directorio_temporal = tempfile.TemporaryDirectory()
        self.ruta = Path(self.directorio_temporal.name) / "test.sqlite3"
        self.abrir()

    # Libera los recursos utilizados durante la prueba.
    def tearDown(self):
        self.persistencia.cerrar()
        self.directorio_temporal.cleanup()

    # Abre la base temporal y crea el servicio de reservaciones.
    def abrir(self):
        self.persistencia = PersistenciaSQLite(self.ruta, datos_iniciales=True)
        self.servicio = ServicioReservaciones(self.persistencia, reloj=lambda: AHORA)

    # Cierra y vuelve a abrir la base para simular un reinicio.
    def reiniciar(self):
        self.persistencia.cerrar()
        self.abrir()

    # Recupera todas las reservaciones guardadas.
    def reservas(self):
        with self.persistencia.lectura() as sesion:
            return sesion.listar_reservaciones()

    # Cambia el estado de una reservación directamente en la base.
    def cancelar(self, identificador):
        with self.persistencia.transaccion() as sesion:
            sesion.conexion.execute(
                "UPDATE reservaciones SET estado='cancelada' WHERE identificador=?", (identificador,))

    # Obtiene las acciones de auditoría de reservaciones.
    def eventos_reserva(self):
        return [(e.accion, e.identificador) for e in Auditoria.consultar(self.persistencia)
                if e.entidad == "reservacion"]

    # Comprueba ID consecutivo, estado activa, carné normalizado y auditoría.
    def test_rf05_creacion_exitosa_y_auditoria(self):
        primera = self.servicio.crear(ACTIVO.lower(), "S01", "2026-09-28", "11:00", "2", "4")
        segunda = self.servicio.crear(ACTIVO, " S02 ", "2026-09-29", "08:00", 1, 1)
        self.assertEqual((primera.identificador, segunda.identificador), ("R0001", "R0002"))
        self.assertEqual(
            (primera.carne, primera.codigo_sala, primera.duracion, primera.estado),
            (ACTIVO, "S01", 2, "activa"))
        self.assertEqual(self.reservas(), [primera, segunda])
        self.assertEqual(self.eventos_reserva(), [("creacion", "R0002"), ("creacion", "R0001")])

    # Comprueba que un rechazo no guarde reservas ni auditoría.
    def test_rf05_rechazos_no_alteran_datos(self):
        casos = (
            ("9999999999", "S01", "2026-09-30", "10:00", 1, 1),   # Estudiante inexistente.
            (INACTIVO, "S01", "2026-09-30", "10:00", 1, 1),       # Estudiante inactivo.
            (ACTIVO, "S99", "2026-09-30", "10:00", 1, 1),         # Sala inexistente.
            (ACTIVO, "S04", "2026-09-30", "10:00", 1, 1),         # Fuera de servicio.
            (ACTIVO, "", "2026-09-30", "10:00", 1, 1),            # Sin sala.
            (ACTIVO, "S01", "2026-09-27", "10:00", 1, 1),         # Fecha pasada.
            (ACTIVO, "S01", "2026-09-28", "10:00", 1, 1),         # Hoy, hora pasada.
            (ACTIVO, "S01", "2026-09-30", "10:30", 1, 1),         # Hora no completa.
            (ACTIVO, "S01", "2026-09-30", "19:00", 2, 1),         # Termina después de las 20:00.
            (ACTIVO, "S01", "2026-09-30", "10:00", 3, 1),         # Duración inválida.
            (ACTIVO, "S01", "2026-09-30", "10:00", 1, 5),         # Supera capacidad.
        )
        for datos in casos:
            with self.subTest(datos=datos), self.assertRaises(ErrorValidacion):
                self.servicio.crear(*datos)
        self.assertEqual(self.reservas(), [])
        self.assertEqual(self.eventos_reserva(), [])

    # Comprueba conflicto, reserva consecutiva y reserva cancelada con datos guardados.
    def test_rn09_conflicto_consecutiva_y_cancelada(self):
        self.servicio.crear(ACTIVO, "S01", "2026-09-30", "10:00", 2, 1)
        with self.assertRaisesRegex(ErrorValidacion, "R0001"):
            self.servicio.crear(OTRO_ACTIVO, "S01", "2026-09-30", "11:00", 1, 1)
        self.assertEqual(self.servicio.crear(OTRO_ACTIVO, "S01", "2026-09-30", "12:00", 1, 1).identificador, "R0002")
        self.cancelar("R0001")
        self.assertEqual(self.servicio.crear(OTRO_ACTIVO, "S01", "2026-09-30", "10:00", 1, 1).identificador, "R0003")

    # Comprueba que la cuarta reserva activa se rechace y que la cancelada no cuente.
    def test_rn11_maximo_tres_reservas(self):
        for fecha in ("2026-09-29", "2026-09-30", "2026-10-01"):
            self.servicio.crear(ACTIVO, "S01", fecha, "10:00", 1, 1)
        with self.assertRaisesRegex(ErrorValidacion, "3 reservaciones"):
            self.servicio.crear(ACTIVO, "S02", "2026-10-02", "10:00", 1, 1)
        self.cancelar("R0001")
        self.assertEqual(self.servicio.crear(ACTIVO, "S02", "2026-10-02", "10:00", 1, 1).identificador, "R0004")

    # Comprueba que el ID continúe después de reiniciar y no se reutilice.
    def test_rn13_reinicio_conserva_reservas_e_ids(self):
        primera = self.servicio.crear(ACTIVO, "S01", "2026-09-30", "10:00", 2, 3)
        self.cancelar(primera.identificador)
        self.reiniciar()
        segunda = self.servicio.crear(ACTIVO, "S01", "2026-09-30", "10:00", 1, 1)
        self.assertEqual(segunda.identificador, "R0002")
        self.assertEqual([r.estado for r in self.reservas()], ["cancelada", "activa"])

    # Comprueba que un fallo de auditoría revierte la reservación completa.
    def test_rnf06_fallo_de_auditoria_revierte(self):
        self.persistencia.conexion.execute(
            "CREATE TRIGGER bloquear BEFORE INSERT ON auditoria "
            "WHEN NEW.entidad = 'reservacion' BEGIN SELECT RAISE(ABORT,'fallo'); END")
        with self.assertRaises(ErrorPersistencia):
            self.servicio.crear(ACTIVO, "S01", "2026-09-30", "10:00", 1, 1)
        self.assertEqual(self.reservas(), [])
        self.persistencia.conexion.execute("DROP TRIGGER bloquear")
        self.assertEqual(self.servicio.crear(ACTIVO, "S01", "2026-09-30", "10:00", 1, 1).identificador, "R0001")

    # Comprueba que la disponibilidad informe conflictos sin modificar la base.
    def test_rf08_disponibilidad_sin_modificar(self):
        self.servicio.crear(ACTIVO, "S01", "2026-09-30", "10:00", 1, 1)
        antes = self.persistencia.conexion.execute("SELECT ultimo FROM secuencia_reservaciones").fetchone()
        ocupada = self.servicio.consultar_disponibilidad("S01", "2026-09-30", "09:00", 2)
        self.assertEqual([r.identificador for r in ocupada.conflictos], ["R0001"])
        self.assertTrue(self.servicio.consultar_disponibilidad("S01", "2026-09-30", "11:00", 1).disponible)
        for datos in (("S04", "2026-09-30", "10:00", 1), ("S99", "2026-09-30", "10:00", 1),
                      ("S01", "30-09-2026", "10:00", 1), ("S01", "2026-09-30", "07:00", 1),
                      ("S01", "2026-09-30", "10:00", 4)):
            with self.subTest(datos=datos), self.assertRaises(ErrorValidacion):
                self.servicio.consultar_disponibilidad(*datos)
        self.assertEqual(len(self.reservas()), 1)
        self.assertEqual(
            self.persistencia.conexion.execute("SELECT ultimo FROM secuencia_reservaciones").fetchone(), antes)
        self.assertEqual(len(self.eventos_reserva()), 1)

    def test_rf14_conflicto_no_guarda_serie_parcial(self):
        ocupada = self.servicio.crear(
            OTRO_ACTIVO, "S01", "2026-10-06", "10:00", 1, 1
        )

        with self.assertRaisesRegex(ErrorValidacion, "Semana 2026-10-06"):
            self.servicio.crear_serie(
                ACTIVO, "S01", "2026-09-29", "10:00", 1, 2, 3
            )

        self.assertEqual(self.reservas(), [ocupada])
        with self.persistencia.lectura() as sesion:
            self.assertEqual(sesion.listar_ocurrencias_serie("S0002"), [])

        siguiente = self.servicio.crear(
            ACTIVO, "S02", "2026-09-29", "10:00", 1, 1
        )
        self.assertEqual(siguiente.identificador, "R0002")

    # Desde la segunda ocurrencia, cancela la segunda y la tercera.
    def test_rf14_cancelar_futuras_conserva_anteriores(self):
        id_serie, reservas = self.servicio.crear_serie(
            ACTIVO, "S01", "2026-09-29", "10:00", 1, 2, 3
        )

        canceladas = self.servicio.cancelar_futuras_serie(
            reservas[1].identificador
        )

        self.assertEqual(id_serie, "S0001")
        self.assertEqual(
            [r.identificador for r in canceladas],
            ["R0002", "R0003"],
        )
        with self.persistencia.lectura() as sesion:
            ocurrencias = sesion.listar_ocurrencias_serie(id_serie)
        self.assertEqual(
            [r.estado for r in ocurrencias],
            ["activa", "cancelada", "cancelada"],
        )
        self.assertEqual(
            self.eventos_reserva()[:2],
            [("cancelacion", "R0003"), ("cancelacion", "R0002")],
        )
        
    # Comprueba reservas de hoy, próximas, ocupación y filtros combinados.
    def test_rf15_panel_y_filtros(self):
        vacio = self.servicio.panel()
        self.assertEqual((vacio.hoy, vacio.proximas, vacio.filtradas), ([], [], []))
        self.assertEqual([item.codigo for item in vacio.ocupacion], ["S01", "S02", "S03", "S04", "S05"])
        self.servicio.crear(ACTIVO, "S01", "2026-09-28", "11:00", 2, 1)       # R0001 hoy, próxima.
        self.servicio.crear(ACTIVO, "S02", "2026-09-29", "08:00", 1, 1)       # R0002 próxima.
        self.servicio.crear(OTRO_ACTIVO, "S01", "2026-09-29", "09:00", 1, 1)  # R0003 se cancela.
        self.cancelar("R0003")

        panel = self.servicio.panel()
        self.assertEqual([r.identificador for r in panel.hoy], ["R0001"])
        self.assertEqual([r.identificador for r in panel.proximas], ["R0001", "R0002"])
        ocupacion = {item.codigo: item for item in panel.ocupacion}
        self.assertEqual((ocupacion["S01"].horas_reservadas, ocupacion["S01"].porcentaje), (2, 17))
        self.assertEqual(ocupacion["S02"].horas_reservadas, 0)
        self.assertEqual(len(panel.filtradas), 3)

        self.assertEqual([r.identificador for r in self.servicio.panel("2026-09-29", "S01", "").filtradas], ["R0003"])
        self.assertEqual(self.servicio.panel("2026-09-29", "S01", "activa").filtradas, [])
        self.assertEqual([r.identificador for r in self.servicio.panel("", "", "cancelada").filtradas], ["R0003"])
        self.assertEqual(self.servicio.panel("2026-09-29").fecha_ocupacion, "2026-09-29")
        for filtros in (("29-09-2026", "", ""), ("", "S99", ""), ("", "", "pendiente")):
            with self.subTest(filtros=filtros), self.assertRaises(ErrorValidacion):
                self.servicio.panel(*filtros)


class InterfazReservacionesTest(unittest.TestCase):
    # Prepara la aplicación completa con una base en memoria y datos iniciales.
    def setUp(self):
        try:
            ventana_prueba = tk.Tk()
        except tk.TclError as error:
            self.skipTest(f"Tk no disponible: {error}")
        ventana_prueba.destroy()
        from solucion.aplicacion import Aplicacion
        directorio_temporal = tempfile.TemporaryDirectory()
        self.addCleanup(directorio_temporal.cleanup)
        self.ruta = Path(directorio_temporal.name) / "test.sqlite3"
        self.persistencia = PersistenciaSQLite(self.ruta, datos_iniciales=True)
        self.addCleanup(self.persistencia.cerrar)
        reloj = patch("solucion.reservaciones.datetime")
        self.reloj = reloj.start()
        self.reloj.now.return_value = AHORA
        self.reloj.fromisoformat.side_effect = datetime.fromisoformat
        self.addCleanup(reloj.stop)
        self.dialogos = {}
        for nombre in ("showinfo", "showerror", "askyesno"):
            parche = patch(f"solucion.interfaz.messagebox.{nombre}")
            self.dialogos[nombre] = parche.start()
            self.addCleanup(parche.stop)
        self.app = Aplicacion(self.persistencia)
        self.app.withdraw()
        self.vista = self.app.reservaciones

    # Libera la ventana de la prueba.
    def tearDown(self):
        if hasattr(self, "app"):
            try:
                self.app.destroy()
            except tk.TclError:
                pass

    # Completa el formulario de reservación.
    def rellenar(self, sala="S01", fecha="2026-09-30", hora="10:00", duracion="1", cantidad="2"):
        self.vista.variables["carne"].set(ACTIVO)
        texto = next(t for t, codigo in self.vista.salas_por_texto.items() if codigo == sala)
        self.vista.variables["sala"].set(texto)
        for campo, valor in (("fecha", fecha), ("hora", hora), ("duracion", duracion), ("cantidad", cantidad)):
            self.vista.variables[campo].set(valor)

    # Recupera todas las reservaciones guardadas.
    def reservas(self):
        with self.persistencia.lectura() as sesion:
            return sesion.listar_reservaciones()

    # Comprueba que crear desde la vista muestre el ID y actualice el panel.
    def test_rf05_rf15_crear_actualiza_panel(self):
        self.assertEqual(self.app.panel.mensajes["hoy"].cget("text"), "No hay reservaciones activas para hoy.")
        self.assertEqual(len(self.vista.salas_por_texto), 5)
        self.app.abrir_reservaciones()
        self.rellenar(fecha="2026-09-28", hora="11:00")
        self.assertTrue(self.vista.pendiente())
        self.assertTrue(self.vista.guardar())
        self.assertIn("R0001", self.dialogos["showinfo"].call_args.args[1])
        self.assertFalse(self.vista.pendiente())
        self.assertEqual(self.app.panel.tabla_hoy.registros.get_children(), ("R0001",))

    # Comprueba que un error se muestre y conserve el borrador.
    def test_rf05_error_conserva_formulario(self):
        self.rellenar(cantidad="9")
        self.assertFalse(self.vista.guardar())
        self.assertIn("capacidad", self.dialogos["showerror"].call_args.args[1])
        self.assertEqual(self.vista.variables["cantidad"].get(), "9")
        self.assertEqual(self.reservas(), [])

    # Comprueba la consulta de disponibilidad desde la vista.
    def test_rf08_consulta_desde_la_vista(self):
        self.rellenar()
        self.assertTrue(self.vista.guardar())
        self.rellenar(hora="10:00")
        self.assertFalse(self.vista.consultar().disponible)
        self.assertIn("R0001", self.vista.resultado.get())
        self.rellenar(hora="11:00")
        self.assertTrue(self.vista.consultar().disponible)
        self.assertEqual(len(self.reservas()), 1)

    # Comprueba que el cierre detecte el borrador y lo guarde antes de salir.
    def test_rf10_cierre_con_borrador(self):
        self.rellenar()
        with patch("solucion.aplicacion.messagebox.askyesnocancel", return_value=None):
            self.assertFalse(self.app.salir())
        with patch("solucion.aplicacion.messagebox.askyesnocancel", return_value=True):
            self.assertTrue(self.app.salir())
        self.persistencia = PersistenciaSQLite(self.ruta)
        self.addCleanup(self.persistencia.cerrar)
        self.assertEqual([r.identificador for r in self.reservas()], ["R0001"])

    # Comprueba filtros combinados y estado vacío en la vista.
    def test_rf15_filtros_en_la_vista(self):
        self.rellenar()
        self.vista.guardar()
        panel = self.app.panel
        panel.filtro_fecha.set("2026-09-30")
        panel.filtro_sala.set("S02")
        panel.actualizar()
        self.assertEqual(panel.mensajes["filtradas"].cget("text"),
                         "No hay reservaciones que coincidan con los filtros.")
        panel.filtro_sala.set("S01")
        panel.filtro_estado.set("activa")
        panel.actualizar()
        self.assertEqual(panel.tabla_filtrada.registros.get_children(), ("R0001",))
        panel.filtro_fecha.set("30/09/2026")
        self.assertIsNone(panel.actualizar())
        self.dialogos["showerror"].assert_called()


if __name__ == "__main__":
    unittest.main()
