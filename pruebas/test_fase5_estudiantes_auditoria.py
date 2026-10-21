"""Pruebas de estudiantes y auditoría (casos del plan de la Fase 4).

Ejecución: python -m unittest pruebas.test_fase5_estudiantes_auditoria -v
"""
import unittest

from pruebas.fase5_utilidades import CasoFase5

ACTIVO, INACTIVO = "activo", "inactivo"


class BaseEstudiantes(CasoFase5):

    def registrar(self, carne, nombre, correo):
        vista = self.estudiantes()
        vista.limpiar()
        self.llenar(vista, carne=carne, nombre=nombre, correo=correo)
        return self.clic(vista.guardar)

    def editar(self, carne, confirmar=True, **cambios):
        vista = self.estudiantes()
        self.seleccionar(vista.tabla, carne)
        vista.editar()
        self.llenar(vista, **cambios)
        self.msg.respuestas = [confirmar]
        return self.clic(vista.guardar)

    def fila(self, carne):
        return next((f for f in self.filas(self.estudiantes().tabla) if f[0] == carne), None)


# Casos RF-02
class CP_RF02(BaseEstudiantes):

    def test_CP_RF02_01_registro_exitoso(self):
        resultado = self.registrar("2026000001", "Ana Pérez", "ana@example.com")
        self.assertTrue(resultado)
        self.assertEqual(self.fila("2026000001"), ("2026000001", "Ana Pérez", "ana@example.com", ACTIVO))
        self.assertEqual(self.msg.ultimo()[0], "showinfo")

    def test_CP_RF02_02_carne_duplicado_por_capitalizacion(self):
        self.registrar("AB12345678", "Laura Vargas", "laura@example.com")
        self.msg.limpiar()
        self.assertFalse(self.registrar("ab12345678", "Juan Mora", "juan@example.com"))
        tipo, _, texto = self.msg.ultimo()
        self.assertEqual(tipo, "showerror")
        self.assertIn("Carné", texto)
        self.assertIn("ya existe", texto)
        carnes = [f[0].casefold() for f in self.filas(self.estudiantes().tabla)]
        self.assertEqual(carnes.count("ab12345678"), 1)

    def test_CP_RF02_03_nombre_vacio(self):
        antes = self.filas(self.estudiantes().tabla)
        self.assertFalse(self.registrar("2026000002", "", "prueba@example.com"))
        tipo, _, texto = self.msg.ultimo()
        self.assertEqual(tipo, "showerror")
        self.assertTrue(texto.startswith("Nombre"), texto)
        self.assertEqual(self.filas(self.estudiantes().tabla), antes)

    def test_CP_RF02_04_longitud_del_carne(self):
        resultados = {}
        for carne in ("A12345678", "A123456789", "A1234567890"):  # 9, 10 y 11 caracteres
            self.msg.limpiar()
            resultados[len(carne)] = (self.registrar(carne, "Prueba Límite", "limite@example.com"),
                                      self.msg.ultimo()[2])
        self.assertFalse(resultados[9][0]); self.assertIn("Carné", resultados[9][1])
        self.assertTrue(resultados[10][0])
        self.assertFalse(resultados[11][0]); self.assertIn("Carné", resultados[11][1])
        carnes = [f[0] for f in self.filas(self.estudiantes().tabla)]
        self.assertIn("A123456789", carnes)
        self.assertNotIn("A12345678", carnes)
        self.assertNotIn("A1234567890", carnes)


# Casos RF-03
class CP_RF03_SinDatosIniciales(BaseEstudiantes):
    datos_iniciales = False

    def test_CP_RF03_01_consulta_con_varios_estudiantes(self):
        # Se registran en desorden.
        self.registrar("D000000003", "Daniel Ruiz", "daniel@example.com")
        self.registrar("A000000001", "Ana Pérez", "ana@example.com")
        self.registrar("C000000002", "Carlos Mora", "carlos@example.com")
        self.editar("C000000002", estado=INACTIVO)
        vista = self.estudiantes()
        self.assertEqual(list(vista.tabla.registros["columns"]),
                         ["Carné", "Nombre completo", "Correo electrónico", "Estado"])
        self.assertEqual(self.filas(vista.tabla), [
            ("A000000001", "Ana Pérez", "ana@example.com", ACTIVO),
            ("C000000002", "Carlos Mora", "carlos@example.com", INACTIVO),
            ("D000000003", "Daniel Ruiz", "daniel@example.com", ACTIVO),
        ])

    def test_CP_RF03_02_consulta_sin_estudiantes(self):
        vista = self.estudiantes()
        self.assertEqual(self.filas(vista.tabla), [])
        self.assertEqual(vista.mensaje.get(), "No hay estudiantes registrados.")
        self.assertNotIn("showerror", [m[0] for m in self.msg.mensajes])


class CP_RF03(BaseEstudiantes):

    def test_CP_RF03_03_estudiantes_con_diferentes_estados(self):
        filas = {f[0]: f for f in self.filas(self.estudiantes().tabla)}
        self.assertEqual(filas["A001234567"][3], ACTIVO)
        self.assertEqual(filas["C004567890"][3], INACTIVO)


# Casos RF-11
class CP_RF11(BaseEstudiantes):

    def test_CP_RF11_01_modificacion_exitosa(self):
        vista = self.estudiantes()
        self.seleccionar(vista.tabla, "A001234567")
        vista.editar()
        self.assertEqual(str(vista.campos["carne"].cget("state")), "readonly")
        self.llenar(vista, nombre="María Jiménez", correo="maria@example.com")
        self.msg.respuestas = [True]
        self.assertTrue(self.clic(vista.guardar))
        titulos = [m[1] for m in self.msg.mensajes]
        self.assertIn("Confirmar modificación", titulos)
        self.assertEqual(self.msg.ultimo()[0], "showinfo")
        self.assertEqual(self.fila("A001234567"), ("A001234567", "María Jiménez", "maria@example.com", ACTIVO))

    def test_CP_RF11_02_correo_invalido(self):
        original = self.fila("B009876543")
        self.assertFalse(self.editar("B009876543", correo="correo inválido"))
        tipo, _, texto = self.msg.ultimo()
        self.assertEqual(tipo, "showerror")
        self.assertTrue(texto.startswith("Correo"), texto)
        self.assertEqual(self.fila("B009876543"), original)

    def test_CP_RF11_03_inactivacion(self):
        # Reservación previa para revisar el historial.
        previa = self.crear_reservacion("A001234567", "S01", "2026-12-15", "10:00", 1, 2)
        self.assertTrue(self.editar("A001234567", estado=INACTIVO))
        self.assertEqual(self.fila("A001234567")[3], INACTIVO)
        historial = self.app.servicio_reservaciones.buscar_por_estudiante("A001234567")
        self.assertEqual([r.identificador for r in historial], [previa.identificador])
        self.msg.limpiar()
        self.assertFalse(self.reservar_desde_vista("A001234567", "S02", "2026-12-16", "10:00", 1, 2))
        tipo, _, texto = self.msg.ultimo()
        self.assertEqual(tipo, "showerror")
        self.assertIn("inactivo", texto)

    def test_CP_RF11_04_reactivacion(self):
        self.assertTrue(self.editar("C004567890", estado=ACTIVO))
        self.assertEqual(self.fila("C004567890"),
                         ("C004567890", "Daniela Rojas", "daniela@universidad.ac.cr", ACTIVO))
        self.msg.limpiar()
        self.assertTrue(self.reservar_desde_vista("C004567890", "S01", "2026-12-15", "10:00", 1, 2))
        self.assertIn("se guardó con el ID", self.msg.ultimo()[2])


# Casos RF-17
class CP_RF17(BaseEstudiantes):

    def eventos(self):
        vista = self.historial_acciones()
        vista.actualizar()
        return self.filas(vista.tabla), vista.mensaje.cget("text")

    def test_CP_RF17_01_auditoria_de_operaciones_exitosas(self):
        self.registrar("2026000003", "Luis Vargas", "luis@example.com")
        self.editar("2026000003", nombre="Luis Alberto Vargas")
        filas, _ = self.eventos()
        self.assertEqual([f[2:] for f in filas], [
            ("modificacion", "estudiante", "2026000003"),
            ("creacion", "estudiante", "2026000003"),
        ])
        for fila in filas:
            self.assertRegex(fila[1], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

    def test_CP_RF17_02_operacion_rechazada_no_se_audita(self):
        self.registrar("AB12345678", "Laura Vargas", "laura@example.com")
        filas_antes, total_antes = self.eventos()
        self.assertFalse(self.registrar("ab12345678", "Juan Mora", "juan@example.com"))
        filas_despues, total_despues = self.eventos()
        self.assertEqual(filas_despues, filas_antes)
        self.assertEqual(total_despues, total_antes)

    def test_CP_RF17_03_historial_protegido(self):
        self.registrar("2026000004", "Elena Soto", "elena@example.com")
        vista = self.historial_acciones()
        filas = self.filas(vista.tabla)
        self.assertEqual(len(filas), 1)

        def controles(widget):
            for hijo in widget.winfo_children():
                yield from controles(hijo)
                clase = hijo.winfo_class()
                if clase in ("TButton", "Button"):
                    yield ("boton", hijo.cget("text"))
                elif clase in ("TEntry", "Entry", "TCombobox", "Text"):
                    yield ("entrada", clase)
        self.assertEqual(list(controles(vista)), [("boton", "Actualizar historial")])
        # Intentar editar o borrar desde la tabla.
        arbol = vista.tabla.registros
        self.assertEqual(arbol.bind(), ())
        item = arbol.get_children()[0]
        arbol.selection_set(item)
        arbol.focus_set(); arbol.focus(item)
        for _ in range(2):
            arbol.event_generate("<ButtonPress-1>", x=20, y=30); arbol.event_generate("<ButtonRelease-1>", x=20, y=30)
        arbol.event_generate("<KeyPress-Delete>")
        self.app.update()
        self.assertEqual(self.filas(self.historial_acciones().tabla), filas)
        guardados = self.persistencia.conexion.execute("SELECT COUNT(*) FROM auditoria").fetchone()[0]
        self.assertEqual(guardados, 1)

    def test_CP_RF17_04_persistencia_de_la_auditoria(self):
        self.editar("B009876543", nombre="Carlos Andrés Méndez")
        antes, _ = self.eventos()
        self.assertEqual([f[2:] for f in antes], [("modificacion", "estudiante", "B009876543")])
        self.reiniciar()
        despues, _ = self.eventos()
        self.assertEqual(despues, antes)


if __name__ == "__main__":
    unittest.main(verbosity=2)
