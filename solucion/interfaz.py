import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .auditoria import Auditoria
from .cierre import ParticipanteCierre
from .contratos import ErrorPersistencia
from .reportes import ENCABEZADOS, exportar_csv
from .validaciones import ErrorValidacion


class TablaRegistros(ttk.Frame):
    # Inicializa las dependencias y el estado del componente.
    def __init__(self, padre, columnas):
        super().__init__(padre)
        titulos = [titulo for titulo, _ in columnas]
        self.registros = ttk.Treeview(
            self, columns=titulos, show="headings", selectmode="browse", height=9
        )
        for titulo, ancho in columnas:
            self.registros.heading(titulo, text=titulo)
            self.registros.column(titulo, width=ancho, minwidth=70)
        vertical = ttk.Scrollbar(self, orient="vertical", command=self.registros.yview)
        horizontal = ttk.Scrollbar(self, orient="horizontal", command=self.registros.xview)
        self.registros.configure(
            yscrollcommand=vertical.set, xscrollcommand=horizontal.set
        )
        self.registros.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

    # Sustituye las filas de la tabla por los registros recibidos.
    def reemplazar(self, filas):
        self.registros.delete(*self.registros.get_children())
        for identificador, valores in filas:
            self.registros.insert("", "end", iid=identificador, values=valores)


class VistaEstudiantes(ttk.Frame):
    CAMPOS = ("carne", "nombre", "correo", "estado")

    # Inicializa las dependencias y el estado del componente.
    def __init__(self, padre, servicio):
        super().__init__(padre, padding=12)
        self.servicio = servicio
        self.carne_seleccionado = None
        self.estudiantes_por_fila = {}
        self.variables = {campo: tk.StringVar(self) for campo in self.CAMPOS}
        self.mensaje = tk.StringVar(self)
        self._crear_formulario()
        self.tabla = TablaRegistros(self, (
            ("Carné", 135), ("Nombre completo", 235),
            ("Correo electrónico", 270), ("Estado", 90),
        ))
        self.tabla.pack(fill="both", expand=True)
        self._crear_acciones()
        self.limpiar()
        self.actualizar()

    # Construye los campos y acciones de edición del estudiante.
    def _crear_formulario(self):
        formulario = ttk.LabelFrame(self, text="Datos del estudiante", padding=12)
        formulario.pack(fill="x", pady=(0, 12))
        self.campos = {}
        etiquetas = ("Carné", "Nombre completo", "Correo electrónico", "Estado")
        for indice, (campo, etiqueta) in enumerate(zip(self.CAMPOS, etiquetas)):
            ttk.Label(formulario, text=etiqueta).grid(
                row=indice, column=0, sticky="w", padx=(0, 12), pady=4
            )
            if campo == "estado":
                control = ttk.Combobox(
                    formulario, textvariable=self.variables[campo],
                    values=("activo", "inactivo"), state="disabled",
                )
            else:
                control = ttk.Entry(
                    formulario, textvariable=self.variables[campo], width=55
                )
            control.grid(row=indice, column=1, sticky="ew", pady=4)
            self.campos[campo] = control
        formulario.columnconfigure(1, weight=1)
        botones = ttk.Frame(formulario)
        botones.grid(row=4, column=1, sticky="w", pady=(10, 0))
        self.boton_guardar = ttk.Button(
            botones, text="Registrar estudiante", command=self.guardar
        )
        self.boton_guardar.pack(side="left")
        ttk.Button(botones, text="Cancelar", command=self.cancelar).pack(
            side="left", padx=8
        )

    # Construye los controles de consulta y selección de estudiantes.
    def _crear_acciones(self):
        acciones = ttk.Frame(self)
        acciones.pack(fill="x", pady=8)
        ttk.Button(acciones, text="Editar seleccionado", command=self.editar).pack(side="left")
        ttk.Button(acciones, text="Actualizar lista", command=self.actualizar).pack(
            side="left", padx=8
        )
        ttk.Label(self, textvariable=self.mensaje).pack(anchor="w")

    # Obtiene los valores actuales del formulario.
    def valores(self):
        return tuple(self.variables[campo].get() for campo in self.CAMPOS)

    # Detecta diferencias respecto al último estado confirmado del formulario.
    def pendiente(self):
        return self.valores() != self.valores_originales

    # Restablece el formulario para registrar un nuevo estudiante.
    def limpiar(self):
        self.carne_seleccionado = None
        for campo, variable in self.variables.items():
            variable.set("activo" if campo == "estado" else "")
        self.campos["carne"].configure(state="normal")
        self.campos["estado"].configure(state="disabled")
        self.boton_guardar.configure(text="Registrar estudiante")
        self.valores_originales = self.valores()

    # Solicita confirmación cuando se perderían datos pendientes.
    def _confirmar_descarte(self):
        return not self.pendiente() or messagebox.askyesno(
            "Descartar cambios", "¿Descartar los datos del formulario sin guardar?", parent=self
        )

    # Descarta el formulario después de obtener la confirmación necesaria.
    def cancelar(self):
        if self._confirmar_descarte():
            self.limpiar()

    # Carga el estudiante seleccionado y bloquea la edición del carné.
    def editar(self):
        seleccion = self.tabla.registros.selection()
        if not seleccion:
            messagebox.showinfo(
                "Seleccionar estudiante", "Seleccione un estudiante en la lista.", parent=self
            )
            return
        if not self._confirmar_descarte():
            return
        # Se conserva el objeto para no convertir carnés numéricos ni perder ceros iniciales.
        estudiante = self.estudiantes_por_fila[seleccion[0]]
        self.carne_seleccionado = estudiante.carne
        for campo in self.CAMPOS:
            self.variables[campo].set(getattr(estudiante, campo))
        self.campos["carne"].configure(state="readonly")
        self.campos["estado"].configure(state="readonly")
        self.boton_guardar.configure(text="Guardar modificación")
        self.valores_originales = self.valores()

    # Confirma y solicita el registro o la modificación del estudiante.
    def guardar(self):
        carne, nombre, correo, estado = self.valores()
        try:
            if self.carne_seleccionado is None:
                self.servicio.registrar(carne, nombre, correo)
            else:
                if not messagebox.askyesno(
                    "Confirmar modificación",
                    f"¿Guardar los cambios de {self.carne_seleccionado}?\nEstado: {estado}",
                    parent=self,
                ):
                    return False
                self.servicio.modificar(self.carne_seleccionado, nombre, correo, estado)
        except (ErrorValidacion, ErrorPersistencia) as error:
            messagebox.showerror("No se pudo guardar", str(error), parent=self)
            return False
        self.limpiar()
        self.actualizar()
        messagebox.showinfo(
            "Guardado", "Los datos del estudiante se guardaron correctamente.", parent=self
        )
        return True

    # Recarga los registros y el estado vacío de la vista.
    def actualizar(self):
        try:
            estudiantes = self.servicio.consultar()
        except (ErrorValidacion, ErrorPersistencia) as error:
            messagebox.showerror("Consulta no disponible", str(error), parent=self)
            return
        self.estudiantes_por_fila = {
            str(indice): estudiante for indice, estudiante in enumerate(estudiantes)
        }
        self.tabla.reemplazar(
            (identificador, (estudiante.carne, estudiante.nombre, estudiante.correo, estudiante.estado))
            for identificador, estudiante in self.estudiantes_por_fila.items()
        )
        self.mensaje.set(
            f"{len(estudiantes)} estudiantes registrados."
            if estudiantes else "No hay estudiantes registrados."
        )

    # Expone las operaciones del formulario al coordinador de cierre.
    def participante_cierre(self):
        return ParticipanteCierre("Estudiantes", self.pendiente, self.guardar, self.limpiar)


class VistaAuditoria(ttk.Frame):
    # Inicializa las dependencias y el estado del componente.
    def __init__(self, padre, persistencia):
        super().__init__(padre, padding=12)
        self.persistencia = persistencia
        ttk.Label(self, text="Historial de acciones · Solo lectura").pack(anchor="w", pady=(0, 8))
        self.tabla = TablaRegistros(self, (
            ("ID", 50), ("Fecha y hora", 235), ("Acción", 130),
            ("Entidad", 140), ("Identificador", 170),
        ))
        self.tabla.pack(fill="both", expand=True)
        ttk.Button(self, text="Actualizar historial", command=self.actualizar).pack(anchor="w", pady=8)
        self.mensaje = ttk.Label(self)
        self.mensaje.pack(anchor="w")
        self.actualizar()

    # Recarga los registros y el estado vacío de la vista.
    def actualizar(self):
        try:
            eventos = Auditoria.consultar(self.persistencia)
        except ErrorPersistencia as error:
            messagebox.showerror("Historial no disponible", str(error), parent=self)
            return
        self.tabla.reemplazar(
            (str(evento.id), (evento.id, evento.fecha_hora, evento.accion, evento.entidad, evento.identificador))
            for evento in eventos
        )
        self.mensaje.configure(
            text=f"{len(eventos)} acciones registradas." if eventos else "No hay acciones registradas."
        )


class VistaSalas(ttk.Frame):
    CAMPOS = ("codigo", "nombre", "capacidad", "estado")

    # Inicializa las dependencias y el estado del componente.
    def __init__(self, padre, servicio):
        super().__init__(padre, padding=12)
        self.servicio = servicio
        self.codigo_seleccionado = None
        self.salas_por_fila = {}
        self.variables = {campo: tk.StringVar(self) for campo in self.CAMPOS}
        self.mensaje = tk.StringVar(self)
        self._crear_formulario()
        self.tabla = TablaRegistros(self, (
            ("Código", 110), ("Nombre", 260), ("Capacidad", 110), ("Estado", 160),
        ))
        self.tabla.pack(fill="both", expand=True)
        self._crear_acciones()
        self.limpiar()
        self.actualizar()

    # Construye los campos y acciones de edición de la sala.
    def _crear_formulario(self):
        formulario = ttk.LabelFrame(self, text="Datos de la sala", padding=12)
        formulario.pack(fill="x", pady=(0, 12))
        self.campos = {}
        etiquetas = ("Código", "Nombre", "Capacidad", "Estado")
        for indice, (campo, etiqueta) in enumerate(zip(self.CAMPOS, etiquetas)):
            ttk.Label(formulario, text=etiqueta).grid(
                row=indice, column=0, sticky="w", padx=(0, 12), pady=4
            )
            if campo == "estado":
                control = ttk.Combobox(
                    formulario, textvariable=self.variables[campo],
                    values=("disponible", "fuera_de_servicio"), state="readonly",
                )
            else:
                control = ttk.Entry(formulario, textvariable=self.variables[campo], width=55)
            control.grid(row=indice, column=1, sticky="ew", pady=4)
            self.campos[campo] = control
        formulario.columnconfigure(1, weight=1)
        botones = ttk.Frame(formulario)
        botones.grid(row=4, column=1, sticky="w", pady=(10, 0))
        self.boton_guardar = ttk.Button(botones, text="Registrar sala", command=self.guardar)
        self.boton_guardar.pack(side="left")
        ttk.Button(botones, text="Cancelar", command=self.cancelar).pack(side="left", padx=8)

    # Construye los controles de consulta y selección de salas.
    def _crear_acciones(self):
        acciones = ttk.Frame(self)
        acciones.pack(fill="x", pady=8)
        ttk.Button(acciones, text="Editar seleccionado", command=self.editar).pack(side="left")
        ttk.Button(acciones, text="Actualizar lista", command=self.actualizar).pack(side="left", padx=8)
        ttk.Label(self, textvariable=self.mensaje).pack(anchor="w")

    # Obtiene los valores actuales del formulario.
    def valores(self):
        return tuple(self.variables[campo].get() for campo in self.CAMPOS)

    # Detecta diferencias respecto al último estado confirmado del formulario.
    def pendiente(self):
        return self.valores() != self.valores_originales

    # Restablece el formulario para registrar una nueva sala.
    def limpiar(self):
        self.codigo_seleccionado = None
        for campo, variable in self.variables.items():
            variable.set("disponible" if campo == "estado" else "")
        self.campos["codigo"].configure(state="normal")
        self.boton_guardar.configure(text="Registrar sala")
        self.valores_originales = self.valores()

    # Solicita confirmación cuando se perderían datos pendientes.
    def _confirmar_descarte(self):
        return not self.pendiente() or messagebox.askyesno(
            "Descartar cambios", "¿Descartar los datos del formulario sin guardar?", parent=self
        )

    # Descarta el formulario después de obtener la confirmación necesaria.
    def cancelar(self):
        if self._confirmar_descarte():
            self.limpiar()

    # Carga la sala seleccionada y bloquea la edición del código.
    def editar(self):
        seleccion = self.tabla.registros.selection()
        if not seleccion:
            messagebox.showinfo("Seleccionar sala", "Seleccione una sala en la lista.", parent=self)
            return
        if not self._confirmar_descarte():
            return
        sala = self.salas_por_fila[seleccion[0]]
        self.codigo_seleccionado = sala.codigo
        for campo in self.CAMPOS:
            self.variables[campo].set(getattr(sala, campo))
        self.campos["codigo"].configure(state="readonly")
        self.boton_guardar.configure(text="Guardar modificación")
        self.valores_originales = self.valores()

    # Confirma y solicita el registro o la modificación de la sala.
    def guardar(self):
        codigo, nombre, capacidad, estado = self.valores()
        try:
            if self.codigo_seleccionado is None:
                self.servicio.registrar(codigo, nombre, capacidad, estado)
            else:
                if not messagebox.askyesno(
                    "Confirmar modificación",
                    f"¿Guardar los cambios de {self.codigo_seleccionado}?\nEstado: {estado}",
                    parent=self,
                ):
                    return False
                self.servicio.modificar(self.codigo_seleccionado, nombre, capacidad, estado)
        except (ErrorValidacion, ErrorPersistencia) as error:
            messagebox.showerror("No se pudo guardar", str(error), parent=self)
            return False
        self.limpiar()
        self.actualizar()
        messagebox.showinfo("Guardado", "Los datos de la sala se guardaron correctamente.", parent=self)
        return True

    # Recarga los registros y el estado vacío de la vista.
    def actualizar(self):
        try:
            salas = self.servicio.consultar()
        except (ErrorValidacion, ErrorPersistencia) as error:
            messagebox.showerror("Consulta no disponible", str(error), parent=self)
            return
        self.salas_por_fila = {str(indice): sala for indice, sala in enumerate(salas)}
        self.tabla.reemplazar(
            (identificador, (sala.codigo, sala.nombre, sala.capacidad, sala.estado))
            for identificador, sala in self.salas_por_fila.items()
        )
        self.mensaje.set(
            f"{len(salas)} salas registradas." if salas else "No hay salas registradas."
        )

    # Expone las operaciones del formulario al coordinador de cierre.
    def participante_cierre(self):
        return ParticipanteCierre("Salas", self.pendiente, self.guardar, self.limpiar)


class VistaReportes(ttk.Frame):
    # Inicializa las dependencias y el estado del componente.
    def __init__(self, padre, servicio):
        super().__init__(padre, padding=12)
        self.servicio = servicio
        self.filas = []
        self.generado = False
        self.variables = {
            "inicial": tk.StringVar(self),
            "final": tk.StringVar(self),
        }
        self.mensaje = tk.StringVar(self)
        self._crear_filtros()
        anchos = (200, 180, 110, 120, 160, 110)
        self.tabla = TablaRegistros(self, tuple(zip(ENCABEZADOS, anchos)))
        self.tabla.pack(fill="both", expand=True)
        ttk.Label(self, textvariable=self.mensaje).pack(anchor="w", pady=8)
        self.actualizar()

    # Construye el rango de fechas y las acciones de consulta y exportación.
    def _crear_filtros(self):
        filtros = ttk.LabelFrame(self, text="Rango del reporte", padding=12)
        filtros.pack(fill="x", pady=(0, 12))
        ttk.Label(filtros, text="Fecha inicial (AAAA-MM-DD)").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(filtros, textvariable=self.variables["inicial"], width=20).grid(
            row=0, column=1, sticky="w", padx=8, pady=4
        )
        ttk.Label(filtros, text="Fecha final (AAAA-MM-DD)").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(filtros, textvariable=self.variables["final"], width=20).grid(
            row=1, column=1, sticky="w", padx=8, pady=4
        )
        botones = ttk.Frame(filtros)
        botones.grid(row=2, column=1, sticky="w", pady=(10, 0))
        ttk.Button(botones, text="Generar reporte", command=self.generar).pack(side="left")
        ttk.Button(botones, text="Exportar CSV", command=self.exportar).pack(side="left", padx=8)

    # Consulta el rango y muestra el resultado sin escribir un archivo.
    def generar(self):
        try:
            filas = self.servicio.generar(self.variables["inicial"].get(), self.variables["final"].get())
        except (ErrorValidacion, ErrorPersistencia) as error:
            messagebox.showerror("No se pudo generar", str(error), parent=self)
            return
        self.filas = filas
        self.generado = True
        self.actualizar()

    # Guarda en CSV el reporte que ya se consultó.
    def exportar(self):
        if not self.generado:
            messagebox.showinfo(
                "Exportar reporte", "Genere el reporte antes de exportarlo.", parent=self
            )
            return
        ruta = filedialog.asksaveasfilename(
            parent=self, title="Exportar reporte", defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
        )
        if not ruta:
            return
        try:
            exportar_csv(self.filas, ruta)
        except OSError as error:
            messagebox.showerror("No se pudo exportar", str(error), parent=self)
            return
        messagebox.showinfo("Exportado", "El reporte se exportó correctamente.", parent=self)

    # Muestra las filas del último reporte generado.
    def actualizar(self):
        self.tabla.reemplazar(
            (str(indice), fila) for indice, fila in enumerate(self.filas)
        )
        if not self.generado:
            self.mensaje.set("Indique la fecha inicial y la fecha final.")
        elif not self.filas:
            self.mensaje.set("No hay reservaciones en el rango indicado.")
        else:
            self.mensaje.set(f"{len(self.filas)} reservaciones en el reporte.")
