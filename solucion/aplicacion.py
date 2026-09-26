import tkinter as tk
from tkinter import messagebox, ttk

from .cierre import CierreControlado
from .contratos import ErrorPersistencia
from .interfaz import VistaEstudiantes, VistaAuditoria
from .estudiantes import ServicioEstudiantes
from .validaciones import ErrorValidacion


class Aplicacion(tk.Tk):
    # Construye las pantallas y conecta el cierre con la persistencia.
    def __init__(self, persistencia):
        super().__init__()
        self.title("Sistema de reservación de salas")
        self.geometry("1050x760")
        self.minsize(760, 620)
        self._crear_inicio()
        self.contenido = ttk.Frame(self)
        ttk.Button(self.contenido, text="Volver al inicio", command=self.volver).pack(anchor="e", padx=16, pady=8)
        self.estudiantes = VistaEstudiantes(self.contenido, ServicioEstudiantes(persistencia))
        self.auditoria = VistaAuditoria(self.contenido, persistencia)
        self.cierre = CierreControlado(persistencia.cerrar, self.destroy)
        self.cierre.agregar(self.estudiantes.participante_cierre())
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
            self.inicio, text="Historial de acciones", command=self.abrir_auditoria
        ).pack(anchor="w", pady=8)

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
        self.auditoria.pack_forget()
        self.contenido.pack(fill="both", expand=True)
        vista.actualizar()
        vista.pack(fill="both", expand=True)

    # Abre la gestión de estudiantes.
    def abrir_estudiantes(self):
        self._mostrar_vista(self.estudiantes)

    # Abre el historial de acciones.
    def abrir_auditoria(self):
        self._mostrar_vista(self.auditoria)

    # Regresa al inicio conservando los formularios pendientes.
    def volver(self):
        self.contenido.pack_forget()
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
