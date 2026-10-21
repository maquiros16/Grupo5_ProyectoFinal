"""Funciones comunes para las pruebas de la Fase 5."""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from solucion.persistencia import PersistenciaSQLite

try:
    import tkinter as tk
    from solucion import aplicacion as modulo_aplicacion
    from solucion import interfaz
    from solucion.aplicacion import Aplicacion
    TK = True
except ImportError:
    TK = False


class RegistroMensajes:
    """Guarda los mensajes de la aplicación y responde las confirmaciones."""

    def __init__(self):
        self.mensajes = []
        self.respuestas = []

    def _registrar(self, tipo):
        def funcion(titulo=None, mensaje=None, **_):
            self.mensajes.append((tipo, titulo, mensaje))
            if tipo in ("askyesno", "askyesnocancel"):
                return self.respuestas.pop(0) if self.respuestas else True
            return "ok"
        return funcion

    def ultimo(self, tipo=None):
        candidatos = [m for m in self.mensajes if tipo is None or m[0] == tipo]
        return candidatos[-1] if candidatos else None

    def limpiar(self):
        self.mensajes.clear()


class CasoFase5(unittest.TestCase):
    """Abre la aplicación con una base de datos temporal."""

    datos_iniciales = True

    def setUp(self):
        if not TK:
            self.skipTest("Requiere Tkinter")
        self.carpeta = Path(tempfile.mkdtemp())
        self.ruta = self.carpeta / "datos" / "reservaciones.sqlite3"
        self.msg = RegistroMensajes()
        parches = []
        for modulo in (interfaz.messagebox, modulo_aplicacion.messagebox):
            for tipo in ("showinfo", "showerror", "showwarning", "askyesno", "askyesnocancel"):
                parches.append(mock.patch.object(modulo, tipo, self.msg._registrar(tipo)))
        for parche in parches:
            parche.start()
            self.addCleanup(parche.stop)
        self.app = None
        self.abrir()

    def tearDown(self):
        self.cerrar_x()
        shutil.rmtree(self.carpeta, ignore_errors=True)

    def abrir(self, datos_iniciales=None):
        inicial = self.datos_iniciales if datos_iniciales is None else datos_iniciales
        self.persistencia = PersistenciaSQLite(self.ruta, datos_iniciales=inicial)
        self.app = Aplicacion(self.persistencia)
        self.app.update()
        return self.app

    def salir(self):
        """Cierra con Archivo > Salir."""
        cerrada = self.app.salir()
        self.app = None if cerrada else self.app
        return cerrada

    def cerrar_x(self):
        """Cierra con la X de la ventana."""
        if self.app is None:
            return True
        comando = self.app.tk.call("wm", "protocol", self.app._w, "WM_DELETE_WINDOW")
        self.app.tk.call(comando)
        cerrada = not self._existe()
        if cerrada:
            self.app = None
        return cerrada

    def reiniciar(self):
        self.salir()
        return self.abrir()

    def _existe(self):
        try:
            return bool(self.app.winfo_exists())
        except tk.TclError:
            return False

    def clic(self, accion):
        """Ejecuta una acción como si se pulsara su botón."""
        try:
            return accion()
        except Exception:
            self.app.report_callback_exception(*sys.exc_info())
            return None

    @staticmethod
    def filas(tabla):
        arbol = tabla.registros
        return [tuple(str(v) for v in arbol.item(i, "values")) for i in arbol.get_children()]

    @staticmethod
    def seleccionar(tabla, columna0):
        arbol = tabla.registros
        for item in arbol.get_children():
            if str(arbol.item(item, "values")[0]) == columna0:
                arbol.selection_set(item)
                return item
        raise AssertionError(f"No se encontró {columna0} en la tabla")

    def estudiantes(self):
        self.app.abrir_estudiantes(); self.app.update()
        return self.app.estudiantes

    def salas(self):
        self.app.abrir_salas(); self.app.update()
        return self.app.salas

    def reportes(self):
        self.app.abrir_reportes(); self.app.update()
        return self.app.reportes

    def historial_acciones(self):
        self.app.abrir_auditoria(); self.app.update()
        return self.app.auditoria

    def reservaciones(self):
        self.app.abrir_reservaciones(); self.app.update()
        return self.app.reservaciones

    def llenar(self, vista, **valores):
        for campo, valor in valores.items():
            vista.variables[campo].set(valor)

    def reservar_desde_vista(self, carne, sala, fecha, hora, duracion, cantidad):
        vista = self.reservaciones()
        texto_sala = next(t for t, c in vista.salas_por_texto.items() if c == sala)
        self.llenar(vista, carne=carne, sala=texto_sala, fecha=fecha, hora=hora,
                    duracion=str(duracion), cantidad=str(cantidad))
        return self.clic(vista.guardar)

    def crear_reservacion(self, carne, sala, fecha, hora, duracion, cantidad):
        """Crea una reservación como precondición."""
        return self.app.servicio_reservaciones.crear(carne, sala, fecha, hora, duracion, cantidad)
