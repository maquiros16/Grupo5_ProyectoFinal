"""Pruebas de salas, persistencia y reportes (casos del plan de la Fase 4).

Los pasos usan los botones de esta aplicación ("Registrar sala", "Editar seleccionado").
Ejecución: python -m unittest pruebas.test_fase5_salas_persistencia_reportes -v
"""
import contextlib
import csv
import io
import sys
import unittest
from unittest import mock

from pruebas.fase5_utilidades import CasoFase5

SALAS_INICIALES = [
    ("S01", "Sala Biblioteca 1", "4", "disponible"),
    ("S02", "Sala Biblioteca 2", "6", "disponible"),
    ("S03", "Laboratorio de estudio", "10", "disponible"),
    ("S04", "Sala multimedia", "8", "fuera de servicio"),  # Ajuste Fase 6 (BUG-01): texto visible
    ("S05", "Cubículo individual", "1", "disponible"),
]
TRAZAS = ("Traceback", "file is not a database", "sqlite3", "Error:", "OverflowError", "ValueError")


class BaseSalas(CasoFase5):

    def registrar_sala(self, codigo, nombre, capacidad):
        vista = self.salas()
        vista.limpiar()
        self.llenar(vista, codigo=codigo, nombre=nombre, capacidad=capacidad)
        return self.clic(vista.guardar)

    def editar_sala(self, codigo, confirmar=True, **cambios):
        vista = self.salas()
        self.seleccionar(vista.tabla, codigo)
        vista.editar()
        self.llenar(vista, **cambios)
        self.msg.respuestas = [confirmar]
        return self.clic(vista.guardar)

    def listado_salas(self):
        return self.filas(self.salas().tabla)

    def sala(self, codigo):
        return next((f for f in self.listado_salas() if f[0] == codigo), None)

    def sin_trazas(self, texto):
        for marca in TRAZAS:
            self.assertNotIn(marca, texto)

    def generar(self, inicial, final):
        vista = self.reportes()
        self.llenar(vista, inicial=inicial, final=final)
        self.msg.limpiar()
        self.clic(vista.generar)
        return vista


# Casos RF-01
class CP_RF01(BaseSalas):

    def test_CP_RF01_01_creacion_en_la_primera_ejecucion(self):
        # La base no existía al abrir la aplicación.
        self.assertTrue(self.ruta.exists())
        self.assertEqual(self.listado_salas(), SALAS_INICIALES)
        estudiantes = self.filas(self.estudiantes().tabla)
        self.assertEqual({(f[0], f[3]) for f in estudiantes},
                         {("A001234567", "activo"), ("B009876543", "activo"), ("C004567890", "inactivo")})
        self.assertNotIn("showerror", [m[0] for m in self.msg.mensajes])

    def test_CP_RF01_02_reinicio_sin_duplicar_ni_sobrescribir(self):
        self.assertTrue(self.registrar_sala("S06", "Sala Posgrado", "12"))
        self.assertTrue(self.editar_sala("S01", capacidad="5"))
        for _ in range(2):
            self.assertTrue(self.salir())
            self.abrir()
            salas = self.listado_salas()
            self.assertEqual(len(salas), 6)
            self.assertEqual(len({f[0] for f in salas}), 6)
            self.assertEqual(self.sala("S01")[2], "5")
            self.assertEqual(self.sala("S06"), ("S06", "Sala Posgrado", "12", "disponible"))
            self.assertEqual(self.sala("S04")[3], "fuera de servicio")  # Ajuste Fase 6 (BUG-01)
        self.assertEqual(len(self.filas(self.estudiantes().tabla)), 3)

    def test_CP_RF01_03_base_de_datos_danada(self):
        from solucion import main as modulo_main
        self.assertTrue(self.salir())
        respaldo = self.ruta.read_bytes()
        self.ruta.write_text("archivo corrupto", encoding="utf-8")
        consola = io.StringIO()
        ventana = mock.MagicMock()
        with mock.patch.object(sys, "argv", ["main", "--db", str(self.ruta)]), \
             mock.patch.object(modulo_main.tk, "Tk", return_value=ventana), \
             mock.patch.object(modulo_main.messagebox, "showerror") as error, \
             contextlib.redirect_stderr(consola):
            codigo = modulo_main.main()
        self.assertEqual(codigo, 1)
        error.assert_called_once()
        titulo, mensaje = error.call_args.args[:2]
        self.assertIn("No se pudo abrir la base de datos", mensaje)
        self.sin_trazas(mensaje)
        self.sin_trazas(consola.getvalue())
        self.ruta.write_bytes(respaldo)
        self.abrir()
        self.assertEqual(len(self.listado_salas()), 5)

    def test_CP_RF01_04_cambios_guardados_sin_cierre_ordenado(self):
        self.assertTrue(self.registrar_sala("S07", "Sala Reuniones", "8"))
        self.msg.limpiar()
        self.assertTrue(self.cerrar_x())
        self.abrir()
        self.assertEqual(self.sala("S07"), ("S07", "Sala Reuniones", "8", "disponible"))
        self.assertNotIn("showerror", [m[0] for m in self.msg.mensajes])


# Casos RF-04
class CP_RF04(BaseSalas):

    def test_CP_RF04_01_listado_inicial_ordenado(self):
        vista = self.salas()
        self.assertEqual(list(vista.tabla.registros["columns"]), ["Código", "Nombre", "Capacidad", "Estado"])
        self.assertEqual([f[0] for f in self.listado_salas()], ["S01", "S02", "S03", "S04", "S05"])
        self.assertTrue(self.sala("S04")[3].startswith("fuera"))
        self.assertEqual(self.sala("S05")[2], "1")

    def test_CP_RF04_02_orden_con_codigos_en_los_extremos(self):
        self.assertTrue(self.registrar_sala("S00", "Sala Pruebas", "2"))
        self.assertTrue(self.registrar_sala("S10", "Sala Magna", "20"))
        esperado = ["S00", "S01", "S02", "S03", "S04", "S05", "S10"]
        self.assertEqual([f[0] for f in self.listado_salas()], esperado)
        self.reiniciar()
        self.assertEqual([f[0] for f in self.listado_salas()], esperado)

    def test_CP_RF04_03_cambio_de_estado_reflejado(self):
        # El estado se cambia con "Editar seleccionado".
        self.editar_sala("S01", confirmar=False, estado="fuera_de_servicio")
        self.assertEqual(self.sala("S01")[3], "disponible")
        self.salas().limpiar()
        self.assertTrue(self.editar_sala("S01", confirmar=True, estado="fuera_de_servicio"))
        self.assertEqual(self.filas(self.app.salas.tabla)[0], ("S01", "Sala Biblioteca 1", "4", "fuera de servicio"))  # Ajuste Fase 6 (BUG-01)
        self.reiniciar()
        self.assertEqual(self.sala("S01")[3], "fuera de servicio")  # Ajuste Fase 6 (BUG-01)
        self.assertTrue(self.editar_sala("S01", estado="disponible"))
        self.assertEqual(self.sala("S01")[3], "disponible")

    def test_CP_RF04_04_estado_visible_y_comprensible(self):
        estados = {f[0]: f[3] for f in self.listado_salas()}
        for codigo in ("S01", "S04"):
            with self.subTest(sala=codigo, estado=estados[codigo]):
                self.assertNotIn("_", estados[codigo], "El estado se muestra con su nombre interno")


# Casos RF-12
class CP_RF12(BaseSalas):

    def test_CP_RF12_01_registro_con_tilde_y_enie(self):
        self.assertTrue(self.registrar_sala("S06", "Sala Muñoz", "12"))
        self.assertEqual(self.msg.ultimo()[0], "showinfo")
        self.assertEqual(self.sala("S06"), ("S06", "Sala Muñoz", "12", "disponible"))
        self.reiniciar()
        self.assertEqual(self.sala("S06"), ("S06", "Sala Muñoz", "12", "disponible"))

    def test_CP_RF12_02_validacion_de_capacidad(self):
        problemas = []
        for capacidad in ("-1", "0", "abc", "2.5", "", "1000000000000000000000000000000"):
            self.msg.limpiar()
            guardado = self.registrar_sala("S07", "Sala Límite", capacidad)
            tipo, _, texto = self.msg.ultimo() or (None, None, "")
            if guardado or self.sala("S07") is not None:
                problemas.append(f"{capacidad!r}: se creó la sala")
            elif tipo != "showerror" or "Capacidad" not in texto:
                problemas.append(f"{capacidad!r}: mensaje poco claro: {texto!r}")
        self.assertTrue(self.app.winfo_exists())
        self.assertTrue(self.registrar_sala("S07", "Sala Límite", "1"))
        self.assertTrue(self.editar_sala("S07", capacidad="2"))
        self.msg.limpiar()
        self.assertFalse(self.editar_sala("S07", capacidad="0"))
        self.assertIn("Capacidad", self.msg.ultimo()[2])
        self.assertEqual(self.sala("S07")[2], "2")
        self.assertEqual(problemas, [])

    def test_CP_RF12_03_codigo_unico_y_no_modificable(self):
        aceptados = []
        for codigo in ("s01", "S01", ""):
            self.msg.limpiar()
            if self.registrar_sala(codigo, "Sala Copia", "3"):
                aceptados.append(codigo)
            else:
                self.assertIn("Código", self.msg.ultimo()[2])
        vista = self.salas()
        self.seleccionar(vista.tabla, "S02")
        vista.editar()
        self.assertEqual(str(vista.campos["codigo"].cget("state")), "readonly")
        vista.limpiar()
        self.assertEqual(aceptados, [], "Se aceptó un código repetido o vacío")
        self.assertEqual(self.listado_salas(), SALAS_INICIALES)

    def test_CP_RF12_04_reduccion_de_capacidad(self):
        r1 = self.crear_reservacion("A001234567", "S02", "2026-12-15", "10:00", 1, 5)
        r2 = self.crear_reservacion("B009876543", "S03", "2026-12-16", "10:00", 1, 8)
        self.app.servicio_reservaciones.cancelar_reservacion(r2.identificador)
        antes = self.persistencia.conexion.execute("SELECT * FROM reservaciones ORDER BY 1").fetchall()
        self.msg.limpiar()
        self.assertFalse(self.editar_sala("S02", capacidad="4"))  # regla 1
        self.assertIn("reservación activa futura", self.msg.ultimo()[2])
        self.assertEqual(self.sala("S02")[2], "6")
        self.assertTrue(self.editar_sala("S02", capacidad="5"))  # regla 2
        self.assertTrue(self.editar_sala("S02", capacidad="8"))  # regla 3
        self.assertTrue(self.editar_sala("S03", capacidad="2"))  # regla 4
        self.assertTrue(self.editar_sala("S01", capacidad="2"))  # regla 5
        despues = self.persistencia.conexion.execute("SELECT * FROM reservaciones ORDER BY 1").fetchall()
        self.assertEqual(despues, antes)
        self.assertEqual((r1.identificador, r2.identificador), ("R0001", "R0002"))


# Casos RF-16
class CP_RF16(BaseSalas):

    def preparar_reservaciones_diciembre(self):
        c = self.crear_reservacion
        ids = [c("A001234567", "S01", "2026-12-14", "09:00", 1, 2).identificador,
               c("A001234567", "S02", "2026-12-15", "10:00", 2, 3).identificador,
               c("B009876543", "S01", "2026-12-16", "14:00", 1, 4).identificador,
               c("B009876543", "S03", "2026-12-17", "08:00", 1, 5).identificador]
        self.app.servicio_reservaciones.cancelar_reservacion(ids[2])
        return ids

    def test_CP_RF16_01_limites_inclusivos(self):
        self.assertEqual(self.preparar_reservaciones_diciembre(), ["R0001", "R0002", "R0003", "R0004"])
        vista = self.generar("2026-12-15", "2026-12-16")  # rango A
        self.assertEqual(list(vista.tabla.registros["columns"]),
                         ["Estudiante", "Sala", "Fecha", "Horario", "Cantidad de personas", "Estado"])
        self.assertEqual(self.filas(vista.tabla), [
            ("Andrea Solano", "Sala Biblioteca 2", "2026-12-15", "10:00 (2 h)", "3", "activa"),
            ("Carlos Méndez", "Sala Biblioteca 1", "2026-12-16", "14:00 (1 h)", "4", "cancelada"),
        ])
        vista = self.generar("2026-12-14", "2026-12-14")  # rango B
        self.assertEqual(self.filas(vista.tabla), [
            ("Andrea Solano", "Sala Biblioteca 1", "2026-12-14", "09:00 (1 h)", "2", "activa"),
        ])

    def test_CP_RF16_02_validacion_del_rango(self):
        reglas = [
            ("", "2026-12-31", "ambas"), ("2026-12-01", "", "ambas"),
            ("abc", "xyz", "AAAA-MM-DD"), ("2026-02-30", "2026-12-31", "AAAA-MM-DD"),
            ("2026-12-20", "2026-12-10", "anterior"),
        ]
        problemas = []
        for inicial, final, esperado in reglas:
            vista = self.generar(inicial, final)
            tipo, _, texto = self.msg.ultimo() or (None, None, "")
            if tipo != "showerror" or vista.generado:
                problemas.append(f"{inicial!r}-{final!r}: no se rechazó")
            elif esperado == "ambas" and not ("obligatori" in texto or "ingrese" in texto.lower()
                                              or "indique" in texto.lower() or "vac" in texto.lower()):
                problemas.append(f"{inicial!r}-{final!r}: el mensaje no pide ingresar la fecha: {texto!r}")
            elif esperado != "ambas" and esperado not in texto:
                problemas.append(f"{inicial!r}-{final!r}: mensaje inesperado: {texto!r}")
        self.assertTrue(self.app.winfo_exists())
        vista = self.generar("2026-12-01", "2026-12-31")  # regla 6
        self.assertTrue(vista.generado)
        self.assertIsNone(self.msg.ultimo("showerror"))
        self.assertEqual(problemas, [])

    def test_CP_RF16_03_exportacion_csv_utf8_completa(self):
        self.app.servicio_reservaciones.estudiantes.registrar("2026000010", "Íñigo Muñoz", "inigo@example.com")
        r1 = self.crear_reservacion("2026000010", "S01", "2026-12-15", "09:00", 2, 3)
        r2 = self.crear_reservacion("2026000010", "S02", "2026-12-16", "10:00", 1, 2)
        self.app.servicio_reservaciones.cancelar_reservacion(r2.identificador)
        vista = self.generar("2026-12-01", "2026-12-31")
        destino = self.carpeta / "reporte_dic.csv"
        with mock.patch("solucion.interfaz.filedialog.asksaveasfilename", return_value=str(destino)):
            self.clic(vista.exportar)
        self.assertEqual(self.msg.ultimo()[0], "showinfo")
        crudo = destino.read_bytes()
        texto = crudo.decode("utf-8")  # falla si no es UTF-8
        self.assertIn("Íñigo Muñoz", texto)
        filas = list(csv.reader(io.StringIO(texto)))
        self.assertEqual(len(filas), 3)  # encabezado + 2 filas
        faltantes = []
        if not any("carn" in e.lower() for e in filas[0]) or "2026000010" not in texto:
            faltantes.append("carné del estudiante")
        if not any(c in texto for c in ("09:00-11:00", "09:00–11:00", "09:00 - 11:00", "11:00")):
            faltantes.append("hora de fin del horario")
        self.assertEqual(faltantes, [], f"El CSV no incluye: {faltantes}. Encabezados: {filas[0]}; fila: {filas[1]}")

    def test_CP_RF16_04_flujos_alternos_de_exportacion(self):
        self.crear_reservacion("A001234567", "S01", "2026-12-14", "09:00", 1, 2)
        destino = self.carpeta / "salida"; destino.mkdir()
        vista = self.reportes()
        with mock.patch("solucion.interfaz.filedialog.asksaveasfilename") as selector:
            self.clic(vista.exportar)  # paso 1
            selector.assert_not_called()
        self.assertIn("Genere el reporte", self.msg.ultimo()[2])
        vista = self.generar("2026-12-01", "2026-12-31")  # pasos 2 y 3
        self.msg.limpiar()
        with mock.patch("solucion.interfaz.filedialog.asksaveasfilename", return_value=""):
            self.clic(vista.exportar)
        self.assertEqual(list(destino.iterdir()), [])
        self.assertEqual(self.msg.mensajes, [])
        vista = self.generar("2027-01-01", "2027-01-31")  # paso 4
        self.assertEqual(vista.mensaje.get(), "No hay reservaciones en el rango indicado.")
        archivo = destino / "vacio.csv"  # paso 5
        self.msg.limpiar()
        with mock.patch("solucion.interfaz.filedialog.asksaveasfilename", return_value=str(archivo)):
            self.clic(vista.exportar)
        avisos = [m for m in self.msg.mensajes if "no hay" in (m[2] or "").lower() or "encabezado" in (m[2] or "").lower()]
        if archivo.exists():
            self.assertTrue(avisos, f"Se creó un archivo solo con encabezados sin avisar. Mensaje: {self.msg.ultimo()}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
