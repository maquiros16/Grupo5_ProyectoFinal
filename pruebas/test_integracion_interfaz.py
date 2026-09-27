"""Pruebas con widgets reales; cuadros de diálogo sustituidos por respuestas deterministas."""
import tkinter as tk
import unittest
from unittest.mock import patch

from solucion.aplicacion import Aplicacion
from solucion.persistencia import PersistenciaSQLite


class InterfazTest(unittest.TestCase):
    # Prepara los recursos necesarios para una prueba independiente.
    def setUp(self):
        try:
            ventana_prueba = tk.Tk()
        except tk.TclError as error:
            self.skipTest(f"Tk no disponible: {error}")
        ventana_prueba.destroy()
        self.persistencia = PersistenciaSQLite(":memory:")
        self.addCleanup(self.persistencia.cerrar)
        self.app = Aplicacion(self.persistencia)
        self.app.withdraw()
        self.vista = self.app.estudiantes
        informacion = patch("solucion.interfaz.messagebox.showinfo")
        errores = patch("solucion.interfaz.messagebox.showerror")
        self.info = informacion.start()
        self.error = errores.start()
        self.addCleanup(informacion.stop)
        self.addCleanup(errores.stop)

    # Libera los recursos utilizados durante la prueba.
    def tearDown(self):
        if hasattr(self, "app"):
            try:
                self.app.destroy()
            except tk.TclError:
                pass

    # Completa los campos del formulario con datos de prueba.
    def rellenar(self, carne="0000000001"):
        for campo, valor in (("carne", carne), ("nombre", "María Núñez"), ("correo", "m@u.ac.cr")):
            self.vista.variables[campo].set(valor)

    # Selecciona el primer estudiante y abre su formulario de edición.
    def seleccionar(self):
        self.vista.tabla.registros.selection_set(self.vista.tabla.registros.get_children()[0])
        self.vista.editar()

    # Comprueba rf03 alta y estado vacio.
    def test_rf02_rf03_alta_y_estado_vacio(self):
        self.assertEqual(self.vista.mensaje.get(), "No hay estudiantes registrados.")
        self.rellenar()
        self.assertTrue(self.vista.guardar())
        self.assertEqual(len(self.vista.tabla.registros.get_children()), 1)
        self.assertFalse(self.vista.pendiente())
        self.app.abrir_auditoria()
        self.assertEqual(len(self.app.auditoria.tabla.registros.get_children()), 1)

    # Comprueba error visible preserva borrador.
    def test_rf02_error_visible_preserva_borrador(self):
        self.rellenar("A1")
        self.assertFalse(self.vista.guardar())
        self.error.assert_called_once()
        self.assertTrue(self.vista.pendiente())
        self.assertEqual(self.vista.servicio.consultar(), [])

    # Comprueba confirmación y carne solo lectura.
    def test_rf11_confirmacion_y_carne_solo_lectura(self):
        self.rellenar()
        self.vista.guardar()
        self.seleccionar()
        self.assertEqual(self.vista.variables["carne"].get(), "0000000001")
        self.assertEqual(str(self.vista.campos["carne"]["state"]), "readonly")
        self.vista.variables["estado"].set("inactivo")
        with patch("solucion.interfaz.messagebox.askyesno", return_value=False):
            self.assertFalse(self.vista.guardar())
        self.assertEqual(self.vista.servicio.consultar()[0].estado, "activo")
        with patch("solucion.interfaz.messagebox.askyesno", return_value=True):
            self.assertTrue(self.vista.guardar())
        self.assertEqual(self.vista.servicio.consultar()[0].estado, "inactivo")

    # Comprueba navegacion conserva borrador y cancelar cierre.
    def test_rf10_navegacion_conserva_borrador_y_cancelar_cierre(self):
        self.rellenar()
        self.app.volver()
        self.assertTrue(self.vista.pendiente())
        with patch("solucion.aplicacion.messagebox.askyesnocancel", return_value=None):
            self.assertFalse(self.app.salir())
        self.assertTrue(self.app.winfo_exists())

    # Comprueba guardar desde cierre.
    def test_rf10_guardar_desde_cierre(self):
        self.rellenar()
        with patch("solucion.aplicacion.messagebox.askyesnocancel", return_value=True):
            self.assertTrue(self.app.salir())
        self.assertTrue(self.app.cierre.finalizado)

    # Comprueba guardado invalido impide cierre.
    def test_rf10_guardado_invalido_impide_cierre(self):
        self.rellenar("A1")
        with patch("solucion.aplicacion.messagebox.askyesnocancel", return_value=True):
            self.assertFalse(self.app.salir())
        self.assertTrue(self.app.winfo_exists())

    # Comprueba menu y x comparten manejador.
    def test_rf10_menu_y_x_comparten_manejador(self):
        self.assertTrue(self.app.protocol("WM_DELETE_WINDOW"))
        archivo = self.app.nametowidget(self.app.nametowidget(self.app["menu"]).entrycget(0, "menu"))
        self.assertEqual(archivo.entrycget(2, "label"), "Salir")
        self.rellenar()
        with patch("solucion.aplicacion.messagebox.askyesnocancel", return_value=None):
            archivo.invoke(2)
        self.assertTrue(self.app.winfo_exists())

    # Verifica navegacion muestra vistas independientes.
    def test_navegacion_muestra_vistas_independientes(self):
        self.app.deiconify()
        self.app.update_idletasks()
        botones = {
            widget.cget("text"): widget
            for widget in self.app.inicio.winfo_children()
            if widget.winfo_class() == "TButton"
        }
        self.assertEqual(
            set(botones),
            {
                "Estudiantes",
                "Salas",
                "Reservaciones",
                "Historial de reservaciones",
                "Reportes",
                "Historial de acciones",
            },
        )
        botones["Estudiantes"].invoke()
        self.app.update_idletasks()
        self.assertTrue(self.app.estudiantes.winfo_ismapped())
        self.assertFalse(self.app.auditoria.winfo_ismapped())
        self.rellenar()
        self.app.volver()
        botones["Historial de acciones"].invoke()
        self.app.update_idletasks()
        self.assertTrue(self.app.auditoria.winfo_ismapped())
        self.assertFalse(self.app.estudiantes.winfo_ismapped())
        self.assertTrue(self.vista.pendiente())

    # Comprueba cierre desde historial detecta borrador.
    def test_rf10_cierre_desde_historial_detecta_borrador(self):
        self.rellenar()
        self.app.abrir_auditoria()
        with patch("solucion.aplicacion.messagebox.askyesnocancel", return_value=None):
            self.assertFalse(self.app.salir())
        self.assertTrue(self.vista.pendiente())
        self.assertTrue(self.app.winfo_exists())

    # Comprueba descartar no guarda estudiante.
    def test_rf10_descartar_no_guarda_estudiante(self):
        self.rellenar()
        with patch("solucion.aplicacion.messagebox.askyesnocancel", return_value=False):
            with patch.object(self.app.cierre, "cerrar_recursos"):
                self.assertTrue(self.app.salir())
        self.assertEqual(self.vista.servicio.consultar(), [])


if __name__ == "__main__":
    unittest.main()
