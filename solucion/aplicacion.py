import tkinter as tk
from tkinter import messagebox, ttk

from .cierre import CierreControlado
from .contratos import ErrorPersistencia
from .reservaciones import ServicioReservaciones
from .estudiantes import ServicioEstudiantes
from .reportes import ServicioReportes
from .salas import ServicioSalas
from .validaciones import ErrorValidacion
from .interfaz import VistaEstudiantes, VistaAuditoria, VistaReportes, VistaSalas, VistaPanel, VistaReservacion, VistaHistorialReservaciones


class Aplicacion(tk.Tk):
    # Construye las pantallas y conecta el cierre con la persistencia.
    def __init__(self, persistencia):
        super().__init__()
        self.title("Sistema de reservación de salas")
        self.geometry("1050x760")
        self.minsize(760, 620)
        self.servicio_reservaciones = ServicioReservaciones(persistencia)
        self._crear_inicio()
        self.contenido = ttk.Frame(self)
        ttk.Button(self.contenido, text="Volver al inicio", command=self.volver).pack(anchor="e", padx=16, pady=8)
        self.estudiantes = VistaEstudiantes(self.contenido, ServicioEstudiantes(persistencia))
        self.salas = VistaSalas(self.contenido, ServicioSalas(persistencia))
        self.reportes = VistaReportes(self.contenido, ServicioReportes(persistencia))
        self.reservaciones = VistaReservacion(self.contenido, self.servicio_reservaciones, al_cambiar=self.panel.actualizar)
        self.historial_reservaciones = VistaHistorialReservaciones(self.contenido, self.servicio_reservaciones)
        self.auditoria = VistaAuditoria(self.contenido, persistencia)
        self.cierre = CierreControlado(persistencia.cerrar, self.destroy)
        self.cierre.agregar(self.estudiantes.participante_cierre())
        self.cierre.agregar(self.salas.participante_cierre())
        self.cierre.agregar(self.reservaciones.participante_cierre())
        self._crear_menu()
        self.protocol("WM_DELETE_WINDOW", self.salir)
        self.volver()

    # Construye las opciones de navegación de la pantalla principal.
    def _crear_inicio(self):
        self.inicio = ttk.Frame(self, padding=32)
        ttk.Label(
            self.inicio, text="Sistema de reservación de salas", font=("Segoe UI", 20, "bold")
        ).pack(anchor="w", pady=16)
        ttk.Button(
            self.inicio, text="Estudiantes", command=self.abrir_estudiantes
        ).pack(anchor="w", pady=(20, 8))
        ttk.Button(
            self.inicio, text="Salas", command=self.abrir_salas
        ).pack(anchor="w", pady=8)
        ttk.Button(
            self.inicio, text="Reservaciones", command=self.abrir_reservaciones
        ).pack(anchor="w", pady=8)
        ttk.Button(
            self.inicio, text="Historial de reservaciones",
            command=self.abrir_historial_reservaciones
        ).pack(anchor="w", pady=8)
        ttk.Button(
            self.inicio, text="Reportes", command=self.abrir_reportes
        ).pack(anchor="w", pady=8)
        ttk.Button(
            self.inicio, text="Historial de acciones", command=self.abrir_auditoria
        ).pack(anchor="w", pady=8)
        self.panel = VistaPanel(self.inicio, self.servicio_reservaciones)
        self.panel.pack(fill="both", expand=True, pady=(8, 0))

    # Configura las opciones del menú de la aplicación.
    def _crear_menu(self):
        menu = tk.Menu(self, tearoff=False)
        archivo = tk.Menu(menu, tearoff=False)
        archivo.add_command(label="Inicio", command=self.volver)
        archivo.add_separator()
        archivo.add_command(label="Salir", command=self.salir)
        menu.add_cascade(label="Archivo", menu=archivo)
        self.configure(menu=menu)

    # Presenta un mensaje controlado ante errores inesperados de eventos.
    def report_callback_exception(self, tipo_error, error, traza):
        messagebox.showerror(
            "Operación no completada",
            "No se pudo completar la operación. Revise los datos e intente nuevamente.", parent=self,
        )

    # Actualiza y muestra una sola vista sin descartar formularios.
    def _mostrar_vista(self, vista):
        self.inicio.pack_forget()
        self.estudiantes.pack_forget()
        self.salas.pack_forget()
        self.reportes.pack_forget()
        self.reservaciones.pack_forget()
        self.historial_reservaciones.pack_forget()
        self.auditoria.pack_forget()
        self.contenido.pack(fill="both", expand=True)
        vista.actualizar()
        vista.pack(fill="both", expand=True)

    # Abre la gestión de estudiantes.
    def abrir_estudiantes(self):
        self._mostrar_vista(self.estudiantes)

    # Abre la gestión de salas.
    def abrir_salas(self):
        self._mostrar_vista(self.salas)

    # Abre la consulta y exportación de reportes.
    def abrir_reportes(self):
        self._mostrar_vista(self.reportes)

    # Abre la creación de reservaciones y consulta de disponibilidad.
    def abrir_reservaciones(self):
        self._mostrar_vista(self.reservaciones)

    # Abre la consulta y búsqueda del historial de reservaciones.
    def abrir_historial_reservaciones(self):
        self._mostrar_vista(self.historial_reservaciones)

    # Abre el historial de acciones.
    def abrir_auditoria(self):
        self._mostrar_vista(self.auditoria)

    # Regresa al inicio conservando los formularios pendientes.
    def volver(self):
        self.contenido.pack_forget()
        self.panel.actualizar()
        self.inicio.pack(fill="both", expand=True)

    # Obtiene la decisión de guardar, descartar o cancelar la salida.
    def _decidir_cierre(self, nombres):
        respuesta = messagebox.askyesnocancel(
            "Cambios pendientes",
            "Hay cambios sin guardar en: " + ", ".join(nombres)
            + ".\n¿Desea guardarlos antes de salir?"
            + "\nSí: guardar. No: descartar. Cancelar: continuar trabajando.",
            parent=self,
        )
        if respuesta is None:
            return "cancelar"
        return "guardar" if respuesta else "descartar"

    # Solicita el cierre y mantiene la ventana abierta si ocurre un error.
    def salir(self):
        try:
            return self.cierre.solicitar(self._decidir_cierre)
        except (ErrorPersistencia, ErrorValidacion) as error:
            messagebox.showerror("No se pudo cerrar", str(error), parent=self)
            return False
