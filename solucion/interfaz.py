import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .auditoria import Auditoria
from .cierre import ParticipanteCierre
from .contratos import ErrorPersistencia
from .reportes import ENCABEZADOS, exportar_csv
from .validaciones import ErrorValidacion
from .reglas import (DURACIONES_PERMITIDAS, HORA_APERTURA, HORA_CIERRE, SALA_FUERA_DE_SERVICIO, formato_hora, hora_fin,)


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

COLUMNAS_RESERVA = (
    ("ID", 70), ("Carné", 120), ("Sala", 60), ("Fecha", 100),
    ("Inicio", 70), ("Fin", 70), ("Personas", 80), ("Estado", 90),
)


# Convierte reservaciones en filas para TablaRegistros.
def filas_reserva(reservas):
    return (
        (reserva.identificador, (reserva.identificador, reserva.carne, reserva.codigo_sala, reserva.fecha,
                                 reserva.hora_inicio, hora_fin(reserva), reserva.cantidad_personas,
                                 reserva.estado))
        for reserva in reservas
    )


# Convierte el estado de una sala en un texto comprensible.
def texto_estado_sala(estado):
    return "fuera de servicio" if estado == SALA_FUERA_DE_SERVICIO else estado


class VistaReservacion(ttk.Frame):
    CAMPOS = ("carne", "sala", "fecha", "hora", "duracion", "cantidad")

    # Inicializa las dependencias y el estado del componente.
    def __init__(self, padre, servicio, al_cambiar=None):
        super().__init__(padre, padding=12)
        self.servicio = servicio
        self.al_cambiar = al_cambiar or (lambda: None)
        self.salas_por_texto = {}
        self.variables = {campo: tk.StringVar(self) for campo in self.CAMPOS}
        self.semanas = tk.StringVar(self, value="2")
        self.resultado = tk.StringVar(self)
        self._crear_formulario()
        self.actualizar()
        self.limpiar()

    # Construye los campos y acciones de la reservación.
    def _crear_formulario(self):
        formulario = ttk.LabelFrame(self, text="Datos de la reservación", padding=12)
        formulario.pack(fill="x", pady=(0, 12))
        etiquetas = ("Carné", "Sala", "Fecha (AAAA-MM-DD)", "Hora de inicio (HH:MM)",
                     "Duración (horas)", "Cantidad de personas")
        horas = [formato_hora(hora) for hora in range(HORA_APERTURA, HORA_CIERRE)]
        self.campos = {}
        for indice, (campo, etiqueta) in enumerate(zip(self.CAMPOS, etiquetas)):
            ttk.Label(formulario, text=etiqueta).grid(row=indice, column=0, sticky="w", padx=(0, 12), pady=4)
            if campo == "sala":
                control = ttk.Combobox(formulario, textvariable=self.variables[campo], state="readonly", width=52)
            elif campo == "hora":
                control = ttk.Combobox(formulario, textvariable=self.variables[campo], values=horas, width=52)
            elif campo == "duracion":
                control = ttk.Combobox(
                    formulario, textvariable=self.variables[campo],
                    values=[str(valor) for valor in DURACIONES_PERMITIDAS], state="readonly", width=52,
                )
            else:
                control = ttk.Entry(formulario, textvariable=self.variables[campo], width=55)
            control.grid(row=indice, column=1, sticky="ew", pady=4)
            self.campos[campo] = control
        ttk.Label(formulario, text="Semanas de recurrencia (2 a 8)").grid(
            row=len(self.CAMPOS), column=0, sticky="w", padx=(0, 12), pady=4
        )
        ttk.Combobox(
            formulario,
            textvariable=self.semanas,
            values=[str(n) for n in range(2, 9)],
            state="readonly",
            width=52,
        ).grid(row=len(self.CAMPOS), column=1, sticky="ew", pady=4)
        formulario.columnconfigure(1, weight=1)
        botones = ttk.Frame(formulario)
        botones.grid(row=len(self.CAMPOS) + 1, column=1, sticky="w", pady=(10, 0))
        ttk.Button(
            botones, text="Previsualizar serie", command=self.previsualizar_serie
        ).pack(side="left", padx=8)
        ttk.Button(botones, text="Crear reservación", command=self.guardar).pack(side="left")
        ttk.Button(botones, text="Consultar disponibilidad", command=self.consultar).pack(side="left", padx=8)
        ttk.Button(botones, text="Cancelar", command=self.cancelar).pack(side="left")
        ttk.Button(
            botones, text="Crear serie semanal", command=self.guardar_serie
        ).pack(side="left", padx=8)
        ttk.Label(self, textvariable=self.resultado, wraplength=900).pack(anchor="w", pady=8)

    # Obtiene los valores actuales del formulario.
    def valores(self):
        return tuple(self.variables[campo].get() for campo in self.CAMPOS)

    # Obtiene el código de la sala seleccionada.
    def codigo_sala(self):
        return self.salas_por_texto.get(self.variables["sala"].get(), "")

    # Detecta diferencias respecto al formulario vacío.
    def pendiente(self):
        return (
            self.valores() != self.valores_originales
            or self.semanas.get() != "2"
        )

    # Restablece el formulario para una nueva reservación.
    def limpiar(self):
        for campo, variable in self.variables.items():
            variable.set("1" if campo == "duracion" else "")
        self.variables["fecha"].set(self.servicio.reloj().date().isoformat())
        self.semanas.set("2")
        self.valores_originales = self.valores()

    # Descarta el formulario después de obtener la confirmación necesaria.
    def cancelar(self):
        if not self.pendiente() or messagebox.askyesno(
            "Descartar cambios", "¿Descartar los datos de la reservación sin guardar?", parent=self
        ):
            self.limpiar()
            self.resultado.set("")

    # Recarga la lista de salas conservando la selección.
    def actualizar(self):
        try:
            salas = self.servicio.listar_salas()
        except ErrorPersistencia as error:
            messagebox.showerror("Salas no disponibles", str(error), parent=self)
            return
        seleccion = self.codigo_sala()
        self.salas_por_texto = {
            f"{sala.codigo} · {sala.nombre} · capacidad {sala.capacidad} · {texto_estado_sala(sala.estado)}": sala.codigo
            for sala in salas
        }
        self.campos["sala"].configure(values=list(self.salas_por_texto))
        texto = next((texto for texto, codigo in self.salas_por_texto.items() if codigo == seleccion), "")
        self.variables["sala"].set(texto)

    # Informa si el horario está libre sin guardar nada.
    def consultar(self):
        _, _, fecha, hora, duracion, _ = self.valores()
        try:
            resultado = self.servicio.consultar_disponibilidad(self.codigo_sala(), fecha, hora, duracion)
        except (ErrorValidacion, ErrorPersistencia) as error:
            messagebox.showerror("No se pudo consultar", str(error), parent=self)
            return None
        horario = resultado.horario
        if resultado.disponible:
            self.resultado.set(
                f"Disponible: sala {self.codigo_sala()} el {horario.fecha} de {horario.hora_inicio} a {horario.hora_fin}."
            )
        else:
            choques = ", ".join(f"{r.identificador} ({r.hora_inicio}-{hora_fin(r)})" for r in resultado.conflictos)
            self.resultado.set(f"No disponible: el horario choca con {choques}.")
        return resultado

    def previsualizar_serie(self):
        _, _, fecha, hora, duracion, _ = self.valores()
        try:
            resultados = self.servicio.previsualizar_recurrencia(
                self.codigo_sala(), fecha, hora, duracion, self.semanas.get()
            )
        except (ErrorValidacion, ErrorPersistencia) as error:
            messagebox.showerror("No se pudo previsualizar", str(error), parent=self)
            return

        lineas = []
        for fecha_semana, disponible, conflictos in resultados:
            if disponible:
                lineas.append(f"{fecha_semana}: disponible")
            else:
                detalle = ", ".join(conflictos) if isinstance(conflictos, list) else conflictos
                lineas.append(f"{fecha_semana}: no disponible ({detalle})")

        messagebox.showinfo("Previsualización de la serie", "\n".join(lineas), parent=self)
    # Crea la reservación y muestra el ID asignado.
    
    def guardar_serie(self):
        carne, _, fecha, hora, duracion, cantidad = self.valores()

        try:
            resultados = self.servicio.previsualizar_recurrencia(
                self.codigo_sala(), fecha, hora, duracion, self.semanas.get()
            )
        except (ErrorValidacion, ErrorPersistencia) as error:
            messagebox.showerror("No se pudo crear la serie", str(error), parent=self)
            return False

        if not all(disponible for _, disponible, _ in resultados):
            messagebox.showwarning(
                "Serie no disponible",
                "Hay semanas con conflictos. Revise la previsualización.",
                parent=self,
            )
            return False

        fechas = "\n".join(fecha_semana for fecha_semana, _, _ in resultados)
        if not messagebox.askyesno(
            "Confirmar serie semanal",
            f"¿Crear {len(resultados)} reservaciones en estas fechas?\n\n{fechas}",
            parent=self,
        ):
            return False

        try:
            self.servicio.crear_serie(
                carne, self.codigo_sala(), fecha, hora, duracion,
                cantidad, self.semanas.get()
            )
        except (ErrorValidacion, ErrorPersistencia) as error:
            messagebox.showerror("No se pudo crear la serie", str(error), parent=self)
            return False

        self.limpiar()
        self.resultado.set("Serie semanal creada correctamente.")
        self.al_cambiar()
        messagebox.showinfo("Serie creada", "Se guardaron todas las semanas.", parent=self)
        return True

    def guardar(self):
        carne, _, fecha, hora, duracion, cantidad = self.valores()
        try:
            reservacion = self.servicio.crear(carne, self.codigo_sala(), fecha, hora, duracion, cantidad)
        except (ErrorValidacion, ErrorPersistencia) as error:
            messagebox.showerror("No se pudo crear la reservación", str(error), parent=self)
            return False
        self.limpiar()
        self.resultado.set(f"Última reservación creada: {reservacion.identificador}.")
        self.al_cambiar()
        messagebox.showinfo(
            "Reservación creada",
            f"La reservación se guardó con el ID {reservacion.identificador}.\n"
            f"Sala {reservacion.codigo_sala}, {reservacion.fecha}, "
            f"{reservacion.hora_inicio}-{hora_fin(reservacion)}.",
            parent=self,
        )
        return True

    # Expone las operaciones del formulario al coordinador de cierre.
    def participante_cierre(self):
        return ParticipanteCierre("Reservación", self.pendiente, self.guardar, self.limpiar)

class VistaHistorialReservaciones(ttk.Frame):
    # Construye la consulta completa y la búsqueda por carné.
    def __init__(self, padre, servicio):
        super().__init__(padre, padding=12)
        self.servicio = servicio
        self.carne = tk.StringVar(self)
        self.mensaje = tk.StringVar(self)
        self.id_edicion = tk.StringVar(self)
        self.campos_edicion = {
            campo: tk.StringVar(self)
            for campo in ("sala", "fecha", "hora", "duracion", "cantidad")
        }

        controles = ttk.Frame(self)
        controles.pack(fill="x", pady=(0, 12))
        ttk.Label(controles, text="Carné del estudiante:").pack(side="left")
        ttk.Entry(controles, textvariable=self.carne, width=20).pack(side="left", padx=8)
        ttk.Button(controles, text="Buscar", command=self.buscar).pack(side="left")
        ttk.Button(controles, text="Mostrar todas", command=self.mostrar_todas).pack(side="left", padx=8)
        formulario = ttk.LabelFrame(self, text="Modificar reservación", padding=8)
        formulario.pack(fill="x", pady=(0, 12))

        etiquetas = (
            ("sala", "Código de sala"),
            ("fecha", "Fecha (AAAA-MM-DD)"),
            ("hora", "Hora de inicio (HH:MM)"),
            ("duracion", "Duración (horas)"),
            ("cantidad", "Cantidad de personas"),
        )
        for fila, (campo, etiqueta) in enumerate(etiquetas):
            ttk.Label(formulario, text=etiqueta).grid(
                row=fila, column=0, sticky="w", padx=(0, 8), pady=2
            )
            ttk.Entry(
                formulario, textvariable=self.campos_edicion[campo], width=24
            ).grid(row=fila, column=1, sticky="w", pady=2)

        botones_edicion = ttk.Frame(formulario)
        botones_edicion.grid(row=5, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Button(
            botones_edicion, text="Cargar fila seleccionada",
            command=self.cargar_edicion
        ).pack(side="left")
        ttk.Button(
            botones_edicion, text="Guardar modificación",
            command=self.guardar_edicion
        ).pack(side="left", padx=8)

        self.tabla = TablaRegistros(self, COLUMNAS_RESERVA)
        self.tabla.pack(fill="both", expand=True)
        ttk.Button(
            self, text="Cancelar reservación seleccionada",
            command=self.cancelar_seleccionada
        ).pack(anchor="w", pady=(8, 0))
        ttk.Button(
            self, text="Cancelar semanas futuras de la serie",
            command=self.cancelar_futuras_seleccionadas
        ).pack(anchor="w", pady=(4, 0))
        ttk.Label(self, textvariable=self.mensaje).pack(anchor="w", pady=8)

    # Muestra el historial completo, incluidas las reservas canceladas.
    def actualizar(self):
        self.mostrar_todas()

    def mostrar_todas(self):
        try:
            reservas = self.servicio.consultar()
        except ErrorPersistencia as error:
            messagebox.showerror("No se pudo consultar", str(error), parent=self)
            return
        self.carne.set("")
        self.tabla.reemplazar(filas_reserva(reservas))
        self.mensaje.set(f"{len(reservas)} reservaciones encontradas." if reservas
                         else "No hay reservaciones registradas.")

    # Filtra el historial por un estudiante existente.
    def buscar(self):
        try:
            reservas = self.servicio.buscar_por_estudiante(self.carne.get())
        except (ErrorValidacion, ErrorPersistencia) as error:
            messagebox.showerror("No se pudo buscar", str(error), parent=self)
            return
        self.tabla.reemplazar(filas_reserva(reservas))
        self.mensaje.set(f"{len(reservas)} reservaciones encontradas." if reservas
                         else "Este estudiante no tiene reservaciones.")

    # Carga en el formulario los datos de la reservación seleccionada.
    def cargar_edicion(self):
        seleccion = self.tabla.registros.selection()
        if not seleccion:
            messagebox.showinfo(
                "Modificar reservación",
                "Seleccione una reservación de la tabla.",
                parent=self,
            )
            return

        try:
            reserva = self.servicio.obtener_reservacion(seleccion[0])
        except (ErrorValidacion, ErrorPersistencia) as error:
            messagebox.showerror("No se pudo cargar", str(error), parent=self)
            return

        if reserva.estado != "activa":
            messagebox.showinfo(
                "Modificar reservación",
                "Solo se puede modificar una reservación activa.",
                parent=self,
            )
            return

        self.id_edicion.set(reserva.identificador)
        self.campos_edicion["sala"].set(reserva.codigo_sala)
        self.campos_edicion["fecha"].set(reserva.fecha)
        self.campos_edicion["hora"].set(reserva.hora_inicio)
        self.campos_edicion["duracion"].set(str(reserva.duracion))
        self.campos_edicion["cantidad"].set(str(reserva.cantidad_personas))
        self.mensaje.set(f"Editando la reservación {reserva.identificador}.")

    # Guarda los cambios del formulario y actualiza el historial.
    def guardar_edicion(self):
        identificador = self.id_edicion.get()
        if not identificador:
            messagebox.showinfo(
                "Modificar reservación",
                "Primero seleccione una fila y pulse «Cargar fila seleccionada».",
                parent=self,
            )
            return

        datos = self.campos_edicion
        try:
            modificada = self.servicio.modificar_reservacion(
                identificador,
                datos["sala"].get(),
                datos["fecha"].get(),
                datos["hora"].get(),
                datos["duracion"].get(),
                datos["cantidad"].get(),
            )
        except (ErrorValidacion, ErrorPersistencia) as error:
            messagebox.showerror("No se pudo modificar", str(error), parent=self)
            return

        self.id_edicion.set("")
        for variable in datos.values():
            variable.set("")
        self.mostrar_todas()
        self.mensaje.set(f"Reservación {modificada.identificador} modificada.")
        messagebox.showinfo(
            "Reservación modificada",
            f"Se guardaron los cambios de {modificada.identificador}.",
            parent=self,
        )

    # Cancela la reservación seleccionada después de pedir confirmación.
    def cancelar_seleccionada(self):
        seleccion = self.tabla.registros.selection()
        if not seleccion:
            messagebox.showinfo(
                "Cancelar reservación",
                "Seleccione una reservación de la tabla.",
                parent=self,
            )
            return

        identificador = seleccion[0]
        if not messagebox.askyesno(
            "Confirmar cancelación",
            f"¿Desea cancelar la reservación {identificador}?",
            parent=self,
        ):
            return

        try:
            self.servicio.cancelar_reservacion(identificador)
        except (ErrorValidacion, ErrorPersistencia) as error:
            messagebox.showerror("No se pudo cancelar", str(error), parent=self)
            return

        self.mostrar_todas()
        messagebox.showinfo(
            "Reservación cancelada",
            f"La reservación {identificador} fue cancelada.",
            parent=self,
        )

    def cancelar_futuras_seleccionadas(self):
        seleccion = self.tabla.registros.selection()
        if not seleccion:
            messagebox.showinfo(
                "Cancelar semanas futuras",
                "Seleccione una reservación de la serie en la tabla.",
                parent=self,
            )
            return

        identificador = seleccion[0]
        if not messagebox.askyesno(
            "Confirmar cancelación",
            f"¿Cancelar esta semana y las siguientes de la serie de {identificador}?",
            parent=self,
        ):
            return

        try:
            self.servicio.cancelar_futuras_serie(identificador)
        except (ErrorValidacion, ErrorPersistencia) as error:
            messagebox.showerror("No se pudo cancelar la serie", str(error), parent=self)
            return

        self.mostrar_todas()
        messagebox.showinfo(
            "Serie actualizada",
            "Se cancelaron las reservaciones futuras correspondientes.",
            parent=self,
        )
    
class VistaPanel(ttk.Frame):
    ESTADOS = ("Todos", "activa", "cancelada")

    # Inicializa las dependencias y el estado del componente.
    def __init__(self, padre, servicio):
        super().__init__(padre)
        self.servicio = servicio
        self.filtro_fecha = tk.StringVar(self)
        self.filtro_sala = tk.StringVar(self, "Todas")
        self.filtro_estado = tk.StringVar(self, "Todos")
        self.mensajes = {}
        pestanas = ttk.Notebook(self)
        pestanas.pack(fill="both", expand=True)
        self.tabla_hoy = self._crear_pestana(pestanas, "Reservaciones de hoy", "hoy", COLUMNAS_RESERVA)
        self.tabla_proximas = self._crear_pestana(pestanas, "Próximas reservaciones", "proximas", COLUMNAS_RESERVA)
        self.tabla_ocupacion = self._crear_pestana(pestanas, "Ocupación por sala", "ocupacion", (
            ("Código", 70), ("Sala", 220), ("Estado", 130), ("Horas reservadas", 130), ("Ocupación", 110),
        ))
        busqueda = ttk.Frame(pestanas, padding=8)
        pestanas.add(busqueda, text="Buscar con filtros")
        self._crear_filtros(busqueda)
        self.tabla_filtrada = TablaRegistros(busqueda, COLUMNAS_RESERVA)
        self.tabla_filtrada.pack(fill="both", expand=True)
        self.mensajes["filtradas"] = ttk.Label(busqueda)
        self.mensajes["filtradas"].pack(anchor="w", pady=(6, 0))
        self.actualizar()

    # Crea una pestaña con su tabla y su mensaje de estado vacío.
    def _crear_pestana(self, pestanas, titulo, clave, columnas):
        marco = ttk.Frame(pestanas, padding=8)
        pestanas.add(marco, text=titulo)
        self.mensajes[clave] = ttk.Label(marco)
        self.mensajes[clave].pack(anchor="w", pady=(0, 6))
        tabla = TablaRegistros(marco, columnas)
        tabla.pack(fill="both", expand=True)
        return tabla

    # Construye los filtros combinables por fecha, sala y estado.
    def _crear_filtros(self, padre):
        filtros = ttk.Frame(padre)
        filtros.pack(fill="x", pady=(0, 8))
        ttk.Label(filtros, text="Fecha (AAAA-MM-DD)").pack(side="left")
        ttk.Entry(filtros, textvariable=self.filtro_fecha, width=12).pack(side="left", padx=(4, 12))
        ttk.Label(filtros, text="Sala").pack(side="left")
        self.combo_sala = ttk.Combobox(filtros, textvariable=self.filtro_sala, state="readonly", width=8)
        self.combo_sala.pack(side="left", padx=(4, 12))
        ttk.Label(filtros, text="Estado").pack(side="left")
        ttk.Combobox(
            filtros, textvariable=self.filtro_estado, values=self.ESTADOS, state="readonly", width=10
        ).pack(side="left", padx=(4, 12))
        ttk.Button(filtros, text="Aplicar filtros", command=self.actualizar).pack(side="left")
        ttk.Button(filtros, text="Limpiar filtros", command=self.limpiar_filtros).pack(side="left", padx=8)

    # Quita los filtros y recarga el panel.
    def limpiar_filtros(self):
        self.filtro_fecha.set("")
        self.filtro_sala.set("Todas")
        self.filtro_estado.set("Todos")
        self.actualizar()

    # Recarga todas las secciones del panel y sus estados vacíos.
    def actualizar(self):
        sala = "" if self.filtro_sala.get() == "Todas" else self.filtro_sala.get()
        estado = "" if self.filtro_estado.get() == "Todos" else self.filtro_estado.get()
        try:
            panel = self.servicio.panel(self.filtro_fecha.get().strip(), sala, estado)
        except (ErrorValidacion, ErrorPersistencia) as error:
            messagebox.showerror("Panel no disponible", str(error), parent=self)
            return None
        self.combo_sala.configure(values=["Todas"] + [item.codigo for item in panel.ocupacion])
        self.tabla_hoy.reemplazar(filas_reserva(panel.hoy))
        self.tabla_proximas.reemplazar(filas_reserva(panel.proximas))
        self.tabla_filtrada.reemplazar(filas_reserva(panel.filtradas))
        self.tabla_ocupacion.reemplazar(
            (item.codigo, (item.codigo, item.nombre, texto_estado_sala(item.estado), item.horas_reservadas,
                           "No reservable" if item.estado == SALA_FUERA_DE_SERVICIO else f"{item.porcentaje} %"))
            for item in panel.ocupacion
        )
        self.mensajes["hoy"].configure(
            text=f"Reservaciones activas para hoy: {len(panel.hoy)}."
            if panel.hoy else "No hay reservaciones activas para hoy.")
        self.mensajes["proximas"].configure(
            text=f"Próximas reservaciones activas: {len(panel.proximas)}."
            if panel.proximas else "No hay próximas reservaciones activas.")
        self.mensajes["ocupacion"].configure(
            text=f"Ocupación del {panel.fecha_ocupacion} (horario de 08:00 a 20:00)."
            if panel.ocupacion else "No hay salas registradas.")
        self.mensajes["filtradas"].configure(
            text=f"Reservaciones encontradas: {len(panel.filtradas)}."
            if panel.filtradas else "No hay reservaciones que coincidan con los filtros.")
        return panel