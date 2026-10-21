"""Funciones comunes para las pruebas de reservaciones de la Fase 5 (Personas 3 y 4).

Se apoya en CasoFase5 (fase5_utilidades.py) y agrega:
- un reloj fijo para la aplicación, porque varios casos dependen de "hoy" y de la hora actual;
- accesos a las pantallas de historial y panel;
- operaciones de la pantalla (modificar, cancelar, buscar, consultar disponibilidad).
"""
from datetime import datetime

from pruebas.fase5_utilidades import CasoFase5

# Reloj por defecto: una fecha anterior a las fechas de diciembre usadas en los casos.
AHORA = datetime(2026, 10, 12, 12, 0)

COLUMNAS = ("ID", "Estudiante", "Sala", "Fecha", "Inicio", "Fin", "Personas", "Estado")


class CasoReservaciones(CasoFase5):
    """Abre la aplicación con la base temporal y un reloj controlado."""

    ahora = AHORA

    def abrir(self, datos_iniciales=None):
        app = super().abrir(datos_iniciales)
        self.fijar_reloj(self.ahora)
        return app

    def fijar_reloj(self, momento):
        """Cambia la fecha y hora que usa la aplicación y refresca el panel."""
        self.ahora = momento
        self.app.servicio_reservaciones.reloj = lambda: momento
        self.app.panel.actualizar()

    def base_nueva(self):
        """Cierra la aplicación y la abre con una base de datos vacía (con los datos iniciales)."""
        self.salir()
        for archivo in self.ruta.parent.glob("*"):
            archivo.unlink()
        return self.abrir()

    # ---- Preparación de precondiciones (sin pasar por la pantalla) ----
    @property
    def servicio(self):
        return self.app.servicio_reservaciones

    def preparar(self, carne, sala, fecha, hora, duracion, cantidad, reloj=None):
        """Crea una reservación como precondición; con 'reloj' simula una fecha anterior."""
        actual = self.ahora
        if reloj:
            self.servicio.reloj = lambda: reloj
        try:
            return self.crear_reservacion(carne, sala, fecha, hora, duracion, cantidad)
        finally:
            self.servicio.reloj = lambda: actual

    def cancelar_directo(self, identificador):
        return self.servicio.cancelar_reservacion(identificador)

    # ---- Pantallas ----
    def historial(self):
        self.app.abrir_historial_reservaciones()
        self.app.update()
        vista = self.app.historial_reservaciones
        return vista

    def lista(self):
        """Filas del historial completo (como las ve la persona usuaria)."""
        vista = self.historial()
        vista.mostrar_todas()
        self.app.update()
        return self.filas(vista.tabla)

    def fila_de(self, identificador):
        return next((f for f in self.lista() if f[0] == identificador), None)

    def id_por_fecha(self, fecha, carne=None):
        for f in self.lista():
            if f[3] == fecha and (carne is None or f[1] == carne):
                return f[0]
        return None

    def texto_sala(self, vista, codigo):
        """Texto del combo 'Sala' que corresponde al código; si no existe, se escribe el código tal cual."""
        return next((t for t, c in vista.salas_por_texto.items() if c == codigo), codigo)

    def llenar_reserva(self, carne, sala, fecha, hora, duracion, cantidad):
        vista = self.reservaciones()
        vista.limpiar()
        self.llenar(vista, carne=carne, sala=self.texto_sala(vista, sala), fecha=fecha, hora=hora,
                    duracion=str(duracion), cantidad=str(cantidad))
        return vista

    def intentar_reserva(self, carne, sala, fecha, hora, duracion, cantidad):
        """Llena el formulario y pulsa 'Crear reservación'. Devuelve (resultado, mensaje)."""
        self.msg.limpiar()
        vista = self.llenar_reserva(carne, sala, fecha, hora, duracion, cantidad)
        resultado = self.clic(vista.guardar)
        return resultado, self.msg.ultimo()

    def consultar_disponibilidad(self, sala, fecha, hora, duracion):
        """Pulsa 'Consultar disponibilidad'. Devuelve (resultado, mensaje de error o None, texto mostrado)."""
        self.msg.limpiar()
        vista = self.llenar_reserva("", sala, fecha, hora, duracion, "")
        vista.resultado.set("")
        resultado = self.clic(vista.consultar)
        return resultado, self.msg.ultimo("showerror"), vista.resultado.get()

    def modificar(self, identificador, confirmar=True, **cambios):
        """Selecciona la reservación, la carga, cambia los campos indicados y pulsa 'Guardar modificación'."""
        vista = self.historial()
        vista.mostrar_todas()
        self.seleccionar(vista.tabla, identificador)
        self.msg.limpiar()
        self.clic(vista.cargar_edicion)
        self.llenar_edicion(vista, **cambios)
        self.msg.limpiar()
        return self.clic(vista.guardar_edicion), vista

    @staticmethod
    def llenar_edicion(vista, **valores):
        for campo, valor in valores.items():
            vista.campos_edicion[campo].set(str(valor))

    def cancelar(self, identificador, confirmar=True):
        """Selecciona la reservación y pulsa 'Cancelar reservación seleccionada'."""
        vista = self.historial()
        vista.mostrar_todas()
        self.seleccionar(vista.tabla, identificador)
        self.msg.limpiar()
        self.msg.respuestas = [confirmar]
        self.clic(vista.cancelar_seleccionada)
        return vista

    def buscar(self, carne):
        vista = self.historial()
        vista.carne.set(carne)
        self.msg.limpiar()
        self.clic(vista.buscar)
        return vista

    # ---- Panel ----
    def panel(self):
        self.app.volver()
        self.app.update()
        return self.app.panel

    @staticmethod
    def ids(filas):
        return [f[0] for f in filas]

    def ocupacion(self, panel):
        """{sala: horas reservadas} tal como lo muestra la pestaña 'Ocupación por sala'."""
        return {f[0]: int(f[3]) for f in self.filas(panel.tabla_ocupacion)}

    @staticmethod
    def sin_repetidas(filas):
        ids = [f[0] for f in filas]
        return len(ids) == len(set(ids))
