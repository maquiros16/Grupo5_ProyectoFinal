"""Pruebas de consulta, búsqueda, cancelación, modificación y recurrencia

Cubre RF-06, RF-07, RF-09, RF-13 y RF-14.
Ejecución: python -m unittest pruebas.test_fase5_consulta_cancelacion_modificacion_recurrencia -v
"""
import unittest
from datetime import datetime

from pruebas.fase5_utilidades_reservaciones import CasoReservaciones
from solucion.contratos import Reservacion
from solucion.validaciones import ErrorValidacion

A, B = "A001234567", "B009876543"


def fila(identificador, carne, sala, fecha, inicio, fin, personas, estado="activa"):
    return (identificador, carne, sala, fecha, inicio, fin, str(personas), estado)


class BaseHistorial(CasoReservaciones):

    def preparar_historial(self):
        """Reservaciones del caso CP-RF06-01 (se guardan en desorden y R0002 se cancela)."""
        self.preparar(A, "S01", "2026-12-16", "14:00", 1, 2)   # R0001 activa
        self.preparar(B, "S02", "2026-12-15", "11:00", 2, 3)   # R0002 (se cancela)
        self.preparar(A, "S03", "2026-12-15", "09:00", 1, 4)   # R0003 activa
        self.cancelar_directo("R0002")


ESPERADO_HISTORIAL = [
    fila("R0003", A, "S03", "2026-12-15", "09:00", "10:00", 4),
    fila("R0002", B, "S02", "2026-12-15", "11:00", "13:00", 3, "cancelada"),
    fila("R0001", A, "S01", "2026-12-16", "14:00", "15:00", 2),
]


# Casos RF-06
class CP_RF06(BaseHistorial):

    def test_CP_RF06_01_historial_completo(self):
        self.preparar_historial()
        vista = self.historial()
        self.assertEqual(list(vista.tabla.registros["columns"]),
                         ["ID", "Carné", "Sala", "Fecha", "Inicio", "Fin", "Personas", "Estado"])
        self.assertEqual(self.lista(), ESPERADO_HISTORIAL)

    def test_CP_RF06_02_consulta_sin_registros(self):
        self.msg.limpiar()
        vista = self.historial()
        vista.mostrar_todas()
        self.assertEqual(self.filas(vista.tabla), [])
        self.assertIn("No hay reservaciones", vista.mensaje.get())
        self.assertEqual([m for m in self.msg.mensajes if m[0] == "showerror"], [])

    def test_CP_RF06_03_consulta_despues_de_reiniciar(self):
        self.preparar_historial()
        antes = self.lista()
        self.reiniciar()
        self.assertEqual(self.lista(), antes)
        self.assertEqual(self.lista(), ESPERADO_HISTORIAL)


# Casos RF-07
class CP_RF07(BaseHistorial):

    def test_CP_RF07_01_busqueda_sin_distinguir_mayusculas(self):
        self.preparar_historial()
        problemas = []
        mayusculas = self.filas(self.buscar("A001234567").tabla)
        minusculas = self.filas(self.buscar("a001234567").tabla)
        if sorted(f[0] for f in mayusculas) != ["R0001", "R0003"]:
            problemas.append(f"A001234567 mostró {[f[0] for f in mayusculas]}")
        if minusculas != mayusculas:
            problemas.append(f"a001234567 mostró {[f[0] for f in minusculas]} y A001234567 {[f[0] for f in mayusculas]}")
        con_cancelada = self.filas(self.buscar("B009876543").tabla)
        if [(f[0], f[7]) for f in con_cancelada] != [("R0002", "cancelada")]:
            problemas.append(f"B009876543 mostró {con_cancelada}")
        self.assertEqual(problemas, [])

    def test_CP_RF07_02_estudiante_registrado_sin_reservaciones(self):
        self.preparar_historial()
        self.servicio.estudiantes.registrar("D001234567", "Diana Mora", "diana@example.com")
        vista = self.buscar("D001234567")
        self.assertEqual(self.filas(vista.tabla), [])
        self.assertEqual(vista.mensaje.get(), "Este estudiante no tiene reservaciones.")

    def test_CP_RF07_03_estudiante_inexistente(self):
        self.preparar_historial()
        self.buscar("A001234567")  # deja una tabla previa en pantalla
        vista = self.buscar("Z001234567")
        tipo, titulo, texto = self.msg.ultimo()
        self.assertEqual((tipo, titulo, texto), ("showerror", "No se pudo buscar", "Carné: el estudiante no existe."))
        self.assertNotIn("Z001234567", [f[1] for f in self.filas(vista.tabla)])


# Casos RF-09
class CP_RF09(CasoReservaciones):

    def test_CP_RF09_01_cancelacion_y_liberacion_del_horario(self):
        self.preparar(A, "S01", "2026-12-15", "10:00", 1, 2)
        problemas = []
        resultado, _, texto = self.consultar_disponibilidad("S01", "2026-12-15", "10:00", 1)
        if resultado.disponible:
            problemas.append(f"Antes de cancelar el horario debía estar ocupado: '{texto}'")
        antes = self.fila_de("R0001")
        self.cancelar("R0001", confirmar=True)
        if "Confirmar cancelación" not in [m[1] for m in self.msg.mensajes]:
            problemas.append("No se pidió la confirmación 'Confirmar cancelación'")
        despues = self.fila_de("R0001")
        if despues is None or despues[:7] != antes[:7] or despues[7] != "cancelada":
            problemas.append(f"R0001 antes={antes}, después={despues}")
        resultado, _, texto = self.consultar_disponibilidad("S01", "2026-12-15", "10:00", 1)
        if not resultado.disponible:
            problemas.append(f"Después de cancelar el horario debía estar disponible: '{texto}'")
        self.assertEqual(problemas, [])

    def test_CP_RF09_02_cancelacion_de_id_inexistente(self):
        self.preparar(A, "S01", "2026-12-15", "10:00", 1, 2)
        antes = self.lista()
        with self.assertRaises(ErrorValidacion) as contexto:
            self.servicio.cancelar_reservacion("R9999")
        self.assertIn("no existe", str(contexto.exception))
        self.assertEqual(self.lista(), antes)

    def test_CP_RF09_03_cancelacion_repetida(self):
        self.preparar(A, "S01", "2026-12-15", "10:00", 1, 2)
        self.cancelar_directo("R0001")
        original = self.lista()
        self.cancelar("R0001", confirmar=True)
        tipo, _, texto = self.msg.ultimo()
        self.assertEqual(tipo, "showerror")
        self.assertIn("ya está cancelada", texto)
        self.assertEqual(self.lista(), original)

    def test_CP_RF09_04_persistencia_y_continuidad_del_identificador(self):
        self.preparar(A, "S01", "2026-12-15", "10:00", 1, 2)
        self.cancelar("R0001", confirmar=True)
        self.reiniciar()
        self.assertEqual(self.fila_de("R0001")[7], "cancelada")
        resultado, mensaje = self.intentar_reserva(A, "S01", "2026-12-16", "11:00", 1, 2)
        self.assertTrue(resultado)
        self.assertIn("R0002", mensaje[2])
        self.assertEqual([(f[0], f[7]) for f in self.lista()],
                         [("R0001", "cancelada"), ("R0002", "activa")])


# Casos RF-13
class CP_RF13(CasoReservaciones):

    def test_CP_RF13_01_modificacion_valida_conservando_id(self):
        self.preparar(A, "S01", "2026-12-15", "09:00", 1, 2)
        guardada, _ = self.modificar("R0001", sala="S02", fecha="2026-12-16", hora="14:00", duracion=2, cantidad=5)
        esperada = fila("R0001", A, "S02", "2026-12-16", "14:00", "16:00", 5)
        self.assertTrue(guardada)
        self.assertEqual(self.lista(), [esperada])
        self.reiniciar()
        self.assertEqual(self.lista(), [esperada])

    def test_CP_RF13_02_modificaciones_invalidas_sin_cambios_parciales(self):
        self.preparar(A, "S01", "2026-12-15", "09:00", 1, 2)   # R0001
        self.preparar(B, "S02", "2026-12-16", "10:00", 2, 3)   # R0002
        original = self.lista()
        intentos = [
            ("fecha inexistente", dict(fecha="2026-02-30"), "no existe"),
            ("termina después del cierre", dict(hora="19:00", duracion=2), "20:00"),
            ("duración de 3 horas", dict(duracion=3), "1 o 2"),
            ("5 personas en S01 (capacidad 4)", dict(cantidad=5), "capacidad"),
            ("sala fuera de servicio", dict(sala="S04"), "fuera de servicio"),
            ("horario con conflicto", dict(sala="S02", fecha="2026-12-16", hora="11:00", duracion=1),
             "ya está reservada"),
        ]
        problemas = []
        for nombre, cambios, palabra in intentos:
            guardada, _ = self.modificar("R0001", **cambios)
            mensaje = self.msg.ultimo()
            if guardada or mensaje is None or mensaje[0] != "showerror" or palabra not in mensaje[2]:
                problemas.append(f"{nombre}: guardada={guardada}, mensaje={mensaje}")
            if self.lista() != original:
                problemas.append(f"{nombre}: las reservaciones cambiaron: {self.lista()}")
        self.assertEqual(problemas, [])

    def test_CP_RF13_03_modificacion_de_reservacion_cancelada(self):
        self.preparar(A, "S01", "2026-12-15", "09:00", 1, 2)
        self.cancelar_directo("R0001")
        original = self.lista()
        vista = self.historial()
        vista.mostrar_todas()
        self.seleccionar(vista.tabla, "R0001")
        self.msg.limpiar()
        self.clic(vista.cargar_edicion)
        self.assertEqual(self.msg.ultimo()[2], "Solo se puede modificar una reservación activa.")
        self.assertEqual(vista.id_edicion.get(), "")
        self.assertEqual(self.lista(), original)
        # El servicio también la rechaza si se solicita directamente (la pantalla no es la única barrera).
        with self.assertRaises(ErrorValidacion) as contexto:
            self.servicio.modificar_reservacion("R0001", "S01", "2026-12-16", "11:00", 1, 2)
        self.assertIn("activa", str(contexto.exception))
        self.assertEqual(self.lista(), original)

    def test_CP_RF13_04_horario_consecutivo_y_superposicion(self):
        self.preparar(A, "S01", "2026-12-15", "08:00", 1, 2)   # R0001 08:00-09:00
        self.preparar(B, "S01", "2026-12-15", "10:00", 2, 2)   # R0002 10:00-12:00
        problemas = []
        guardada, _ = self.modificar("R0001", hora="12:00", duracion=1)
        if not guardada or self.fila_de("R0001")[4:6] != ("12:00", "13:00"):
            problemas.append(f"Horario consecutivo: guardada={guardada}, R0001={self.fila_de('R0001')}")
        guardada, _ = self.modificar("R0001", hora="11:00", duracion=1)
        mensaje = self.msg.ultimo()
        if guardada or mensaje[0] != "showerror" or "ya está reservada" not in mensaje[2]:
            problemas.append(f"Superposición: guardada={guardada}, mensaje={mensaje}")
        if self.fila_de("R0001")[4:6] != ("12:00", "13:00") or self.fila_de("R0002")[4:6] != ("10:00", "12:00"):
            problemas.append(f"Horarios finales: {self.lista()}")
        self.assertEqual(problemas, [])

    def test_CP_RF13_05_limite_al_trasladar_una_reserva_pasada(self):
        # La pasada se guarda con un reloj anterior; las futuras, cuando la pasada ya terminó (para no superar el máximo).
        self.preparar(A, "S01", "2026-09-01", "09:00", 1, 2, reloj=datetime(2026, 8, 31, 12, 0))   # R0001
        for fecha in ("2026-12-15", "2026-12-16", "2026-12-17"):
            self.preparar(A, "S01", fecha, "09:00", 1, 2, reloj=datetime(2026, 9, 2, 12, 0))
        self.fijar_reloj(datetime(2026, 10, 12, 12, 0))
        problemas = []
        guardada, _ = self.modificar("R0001", fecha="2026-12-18")
        mensaje = self.msg.ultimo()
        if guardada or mensaje[0] != "showerror":
            problemas.append(f"Primer intento: debía rechazarse. guardada={guardada}, mensaje={mensaje}")
        if self.fila_de("R0001")[3] != "2026-09-01":
            problemas.append(f"R0001 no conservó su fecha original: {self.fila_de('R0001')}")
        self.cancelar("R0002", confirmar=True)
        guardada, _ = self.modificar("R0001", fecha="2026-12-18")
        if not guardada or self.fila_de("R0001")[3] != "2026-12-18":
            problemas.append(f"Segundo intento: debía aceptarse. guardada={guardada}, R0001={self.fila_de('R0001')}")
        futuras = [f for f in self.lista() if f[7] == "activa" and f[3] > "2026-10-12"]
        if len(futuras) != 3:
            problemas.append(f"Debían quedar 3 futuras activas y hay {len(futuras)}: {futuras}")
        self.assertEqual(problemas, [])


# Casos RF-14
class CP_RF14(CasoReservaciones):

    DATOS = (A, "S01", "2026-12-15", "10:00", 1, 2)

    def llenar_serie(self, semanas):
        vista = self.llenar_reserva(*self.DATOS)
        vista.semanas.set(str(semanas))
        return vista

    def test_CP_RF14_01_serie_semanal_valida(self):
        vista = self.llenar_serie(2)
        self.msg.limpiar()
        self.clic(vista.previsualizar_serie)
        titulo, texto = self.msg.ultimo("showinfo")[1:]
        self.assertEqual(titulo, "Previsualización de la serie")
        self.assertIn("2026-12-15: disponible", texto)
        self.assertIn("2026-12-22: disponible", texto)
        self.msg.respuestas = [True]
        self.assertTrue(self.clic(vista.guardar_serie))
        filas = self.lista()
        self.assertEqual([(f[3], f[7]) for f in filas], [("2026-12-15", "activa"), ("2026-12-22", "activa")])
        self.assertEqual(len({f[0] for f in filas}), 2)

    def test_CP_RF14_02_limites_de_ocurrencias_y_maximo_por_estudiante(self):
        problemas = []
        for semanas, guardadas in ((2, 2), (3, 3), (4, 0), (8, 0)):
            self.base_nueva()
            vista = self.llenar_serie(semanas)
            self.msg.limpiar()
            self.msg.respuestas = [True]
            resultado = self.clic(vista.guardar_serie)
            total = len(self.lista())
            if total != guardadas or bool(resultado) != (guardadas > 0):
                problemas.append(f"{semanas} semanas: se esperaban {guardadas} guardadas y hay {total} (resultado={resultado})")
            if guardadas == 0:
                mensaje = self.msg.ultimo("showerror")
                if not mensaje or "máximo" not in mensaje[2]:
                    problemas.append(f"{semanas} semanas: el mensaje no explica el máximo: {mensaje}")
        for semanas in (1, 9):
            self.base_nueva()
            try:
                self.servicio.crear_serie(*self.DATOS, semanas)
                problemas.append(f"{semanas} semanas: el servicio guardó la serie")
            except ErrorValidacion as error:
                if "entre 2 y 8" not in str(error):
                    problemas.append(f"{semanas} semanas: mensaje inesperado '{error}'")
            if self.lista():
                problemas.append(f"{semanas} semanas: quedaron reservaciones guardadas")
        self.assertEqual(problemas, [])

    def test_CP_RF14_03_conflicto_sin_almacenamiento_parcial(self):
        self.preparar(B, "S01", "2026-12-22", "10:00", 1, 2)   # R0001 existente
        original = self.lista()
        vista = self.llenar_serie(3)
        self.msg.limpiar()
        self.clic(vista.previsualizar_serie)
        texto = self.msg.ultimo("showinfo")[2]
        self.assertIn("2026-12-22: no disponible", texto)
        self.assertIn("2026-12-15: disponible", texto)
        self.msg.limpiar()
        self.assertFalse(self.clic(vista.guardar_serie))
        tipo, titulo, texto = self.msg.ultimo()
        self.assertEqual((tipo, titulo), ("showwarning", "Serie no disponible"))
        self.assertIn("conflictos", texto)
        self.assertEqual(self.lista(), original)

    def preparar_serie_de_tres(self):
        self.servicio.crear_serie(A, "S01", "2026-12-15", "10:00", 1, 2, 3)

    def test_CP_RF14_04_cancelacion_individual_de_ocurrencia(self):
        self.preparar_serie_de_tres()
        identificador = self.id_por_fecha("2026-12-22")
        self.cancelar(identificador, confirmar=True)
        problemas = []
        estados = {f[3]: f[7] for f in self.lista()}
        if estados != {"2026-12-15": "activa", "2026-12-22": "cancelada", "2026-12-29": "activa"}:
            problemas.append(f"Estados de las ocurrencias: {estados}")
        resultado, _, texto = self.consultar_disponibilidad("S01", "2026-12-22", "10:00", 1)
        if not resultado.disponible:
            problemas.append(f"El horario cancelado debía quedar disponible: '{texto}'")
        self.assertEqual(problemas, [])

    def test_CP_RF14_05_cancelacion_de_futuras_conservando_pasadas(self):
        self.fijar_reloj(datetime(2026, 10, 12, 12, 0))
        # Se preparan las cuatro ocurrencias de una misma serie directamente en la base de pruebas:
        # el servicio no permite crear una serie con ocurrencias pasadas ni con cuatro activas.
        ocurrencias = [("2026-10-05", "activa"), ("2026-10-12", "activa"),
                       ("2026-10-19", "activa"), ("2026-10-26", "cancelada")]
        with self.persistencia.transaccion() as sesion:
            id_serie = None
            for fecha, estado in ocurrencias:
                identificador = sesion.siguiente_identificador_reservacion()
                id_serie = id_serie or f"S{identificador[1:]}"
                sesion.insertar_reservacion(Reservacion(identificador, A, "S01", fecha, "10:00", 1, 2, estado))
                sesion.insertar_ocurrencia_serie(id_serie, identificador)
        antes = {f[3]: f for f in self.lista()}
        canceladas = self.servicio.cancelar_futuras_serie(antes["2026-10-05"][0])
        despues = {f[3]: f for f in self.lista()}
        problemas = []
        if [r.fecha for r in canceladas] != ["2026-10-19"]:
            problemas.append(f"Se cancelaron {[r.fecha for r in canceladas]} y debía cancelarse solo 2026-10-19")
        if despues["2026-10-19"][7] != "cancelada":
            problemas.append("La ocurrencia futura del 19 no quedó cancelada")
        for fecha in ("2026-10-05", "2026-10-12", "2026-10-26"):
            if despues[fecha] != antes[fecha]:
                problemas.append(f"La ocurrencia del {fecha} cambió: antes={antes[fecha]}, después={despues[fecha]}")
        if len(despues) != 4:
            problemas.append(f"Se eliminaron registros: quedan {len(despues)} de 4")
        self.assertEqual(problemas, [])

    def test_CP_RF14_05_complemento_boton_cancelar_semanas_futuras(self):
        """Complemento de CP-RF14-05 por la pantalla: la ocurrencia elegida es futura (no pasada)."""
        self.servicio.crear_serie(A, "S01", "2026-12-15", "10:00", 1, 2, 3)
        vista = self.historial()
        vista.mostrar_todas()
        self.seleccionar(vista.tabla, self.id_por_fecha("2026-12-22"))
        self.msg.limpiar()
        self.msg.respuestas = [True]
        self.clic(vista.cancelar_futuras_seleccionadas)
        estados = {f[3]: f[7] for f in self.lista()}
        self.assertEqual(estados, {"2026-12-15": "activa", "2026-12-22": "cancelada", "2026-12-29": "cancelada"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
