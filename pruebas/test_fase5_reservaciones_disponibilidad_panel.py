"""Pruebas de creación de reservaciones, disponibilidad y panel (casos de la Fase 4, Persona 3).

Cubre RF-05, RF-08 y RF-15.
Ejecución: python -m unittest pruebas.test_fase5_reservaciones_disponibilidad_panel -v
"""
import os
import unittest
from datetime import datetime

from pruebas.fase5_utilidades_reservaciones import CasoReservaciones
from solucion.validaciones import ErrorValidacion

A, B, INACTIVO = "A001234567", "B009876543", "C004567890"


def fila(identificador, carne, sala, fecha, inicio, fin, personas, estado="activa"):
    return (identificador, carne, sala, fecha, inicio, fin, str(personas), estado)


# Casos RF-05
class CP_RF05(CasoReservaciones):

    def test_CP_RF05_01_creacion_exitosa_y_persistencia(self):
        resultado, mensaje = self.intentar_reserva(A, "S01", "2026-12-15", "10:00", 2, 3)
        self.assertTrue(resultado)
        self.assertEqual(mensaje[0], "showinfo")
        self.assertIn("R0001", mensaje[2])
        esperada = fila("R0001", A, "S01", "2026-12-15", "10:00", "12:00", 3)
        self.assertEqual(self.lista(), [esperada])
        # Salir y volver a abrir.
        self.reiniciar()
        self.assertEqual(self.lista(), [esperada])
        # 2.ª reservación: con los mismos datos habría conflicto de horario, por eso se usa la sala S02.
        resultado, mensaje = self.intentar_reserva(A, "S02", "2026-12-15", "10:00", 2, 3)
        self.assertTrue(resultado)
        self.assertIn("R0002", mensaje[2])
        self.assertEqual(self.ids(self.lista()), ["R0001", "R0002"])

    def test_CP_RF05_02_estudiante_o_sala_no_validos(self):
        intentos = [
            ("carné inexistente", ("Z999999999", "S01"), "no existe"),
            ("estudiante inactivo", (INACTIVO, "S01"), "inactivo"),
            ("sala fuera de servicio", (A, "S04"), "fuera de servicio"),
        ]
        problemas = []
        for nombre, (carne, sala), palabra in intentos:
            resultado, mensaje = self.intentar_reserva(carne, sala, "2026-12-15", "10:00", 1, 2)
            if resultado or mensaje[0] != "showerror" or palabra not in mensaje[2]:
                problemas.append(f"{nombre}: resultado={resultado}, mensaje={mensaje}")
        # La lista "Sala" de la pantalla es de solo lectura y no permite escribir S99: se prueba en el servicio.
        try:
            self.servicio.crear(A, "S99", "2026-12-15", "10:00", 1, 2)
            problemas.append("sala inexistente: el servicio guardó la reservación")
        except ErrorValidacion as error:
            if "no existe" not in str(error):
                problemas.append(f"sala inexistente: mensaje={error}")
        self.assertEqual(problemas, [])
        self.assertEqual(self.lista(), [])

    def test_CP_RF05_03_validacion_de_fecha_y_hora(self):
        # Hora de hoy que ya pasó: el reloj de la prueba es 2026-10-12 12:00.
        rechazos = [
            ("fecha pasada", "2026-01-10", "10:00", 1, "anterior"),
            ("fecha inexistente", "2026-02-30", "10:00", 1, "no existe"),
            ("hoy con hora pasada", "2026-10-12", "11:00", 1, "después de la hora actual"),
            ("hora no completa", "2026-12-15", "10:30", 1, "hora completa"),
            ("antes del horario", "2026-12-15", "07:00", 1, "08:00"),
            ("termina fuera del horario", "2026-12-15", "19:00", 2, "20:00"),
        ]
        problemas = []
        for nombre, fecha, hora, duracion, palabra in rechazos:
            resultado, mensaje = self.intentar_reserva(A, "S01", fecha, hora, duracion, 2)
            if resultado or mensaje[0] != "showerror" or palabra not in mensaje[2]:
                problemas.append(f"{nombre}: resultado={resultado}, mensaje={mensaje}")
        for nombre, hora in (("primera hora permitida", "08:00"), ("última hora de 1 h", "19:00")):
            resultado, mensaje = self.intentar_reserva(A, "S01", "2026-12-15", hora, 1, 2)
            if not resultado or mensaje[0] != "showinfo":
                problemas.append(f"{nombre}: debía guardarse y dio resultado={resultado}, mensaje={mensaje}")
        self.assertEqual(problemas, [])
        self.assertEqual([f[4] for f in self.lista()], ["08:00", "19:00"])

    def test_CP_RF05_04_duracion_capacidad_y_conflictos(self):
        existente = self.preparar(B, "S01", "2026-12-15", "10:00", 2, 2)
        problemas = []
        rechazos = [
            ("duración de 3 horas", "S01", "14:00", 3, 2, "1 o 2"),
            ("más personas que la capacidad", "S01", "14:00", 1, 5, "capacidad"),
            ("mismo horario", "S01", "10:00", 1, 2, "ya está reservada"),
            ("superposición parcial", "S01", "11:00", 2, 2, "ya está reservada"),
        ]
        for nombre, sala, hora, duracion, cantidad, palabra in rechazos:
            resultado, mensaje = self.intentar_reserva(A, sala, "2026-12-15", hora, duracion, cantidad)
            if resultado or mensaje[0] != "showerror" or palabra not in mensaje[2]:
                problemas.append(f"{nombre}: resultado={resultado}, mensaje={mensaje}")
        aceptados = [
            ("capacidad exacta", "S01", "14:00", 1, 4),
            ("horario consecutivo", "S01", "12:00", 1, 2),
            ("mismo horario en otra sala", "S02", "10:00", 2, 2),
        ]
        for nombre, sala, hora, duracion, cantidad in aceptados:
            resultado, mensaje = self.intentar_reserva(A, sala, "2026-12-15", hora, duracion, cantidad)
            if not resultado or mensaje[0] != "showinfo":
                problemas.append(f"{nombre}: debía guardarse y dio resultado={resultado}, mensaje={mensaje}")
        self.assertEqual(problemas, [])
        self.assertEqual(len(self.lista()), 1 + 3)
        self.assertEqual(self.fila_de(existente.identificador)[1], B)


# Casos RF-08
class CP_RF08(CasoReservaciones):

    def preparar_reserva_existente(self):
        # Reservación activa de B009876543 en S01, 2026-12-15, de 10:00 a 12:00.
        return self.preparar(B, "S01", "2026-12-15", "10:00", 2, 2)

    def test_CP_RF08_01_disponibilidad_con_y_sin_conflictos(self):
        self.preparar_reserva_existente()
        casos = [
            ("mismo horario", "S01", "2026-12-15", "10:00", 1, False),
            ("superposición parcial", "S01", "2026-12-15", "11:00", 2, False),
            ("empieza cuando termina", "S01", "2026-12-15", "12:00", 1, True),
            ("otra sala", "S02", "2026-12-15", "10:00", 1, True),
            ("otra fecha", "S01", "2026-12-16", "10:00", 1, True),
        ]
        problemas = []
        for nombre, sala, fecha, hora, duracion, disponible in casos:
            resultado, error, texto = self.consultar_disponibilidad(sala, fecha, hora, duracion)
            if error or resultado is None or resultado.disponible != disponible:
                problemas.append(f"{nombre}: esperado disponible={disponible}, texto='{texto}', error={error}")
            elif disponible and not texto.startswith("Disponible"):
                problemas.append(f"{nombre}: el texto mostrado no indica disponibilidad: '{texto}'")
            elif not disponible and not texto.startswith("No disponible"):
                problemas.append(f"{nombre}: el texto mostrado no indica ocupación: '{texto}'")
        self.assertEqual(problemas, [])

    def test_CP_RF08_02_sala_no_valida_y_campos_vacios(self):
        problemas = []
        # La lista "Sala" de la pantalla es de solo lectura y no permite escribir S99: se prueba en el servicio.
        try:
            self.servicio.consultar_disponibilidad("S99", "2026-12-15", "10:00", 1)
            problemas.append("sala inexistente: el servicio la reportó como válida")
        except ErrorValidacion as error:
            if "no existe" not in str(error):
                problemas.append(f"sala inexistente: mensaje={error}")
        _, error, texto = self.consultar_disponibilidad("S04", "2026-12-15", "10:00", 1)
        if not error or "fuera de servicio" not in error[2] or texto.startswith("Disponible"):
            problemas.append(f"sala fuera de servicio: error={error}, texto='{texto}'")
        # Campos vacíos: el mensaje debe indicar qué campo falta.
        indicadores = ("indique", "obligatorio", "vacío", "falta", "seleccione")
        _, error, texto = self.consultar_disponibilidad("", "2026-12-15", "10:00", 1)
        if not error or not any(p in error[2].lower() for p in indicadores):
            problemas.append(f"sala vacía: el mensaje no indica que falta la sala. Mensaje={error}")
        _, error, texto = self.consultar_disponibilidad("S01", "2026-12-15", "", 1)
        if not error or not any(p in error[2].lower() for p in indicadores):
            problemas.append(f"hora vacía: el mensaje no indica que falta la hora. Mensaje={error}")
        self.assertEqual(problemas, [])

    def test_CP_RF08_03_validacion_de_fecha_hora_y_duracion(self):
        problemas = []
        resultado, error, texto = self.consultar_disponibilidad("S01", "2026-12-15", "08:00", 1)
        if error or resultado is None or not resultado.disponible:
            problemas.append(f"primera hora permitida: error={error}, texto='{texto}'")
        rechazos = [
            ("antes del horario", "S01", "2026-12-15", "07:00", 1, "08:00"),
            ("termina fuera del horario", "S01", "2026-12-15", "19:00", 2, "20:00"),
            ("hora no completa", "S01", "2026-12-15", "10:30", 1, "hora completa"),
            ("duración no permitida", "S01", "2026-12-15", "10:00", 3, "1 o 2"),
            ("fecha inexistente", "S01", "2026-02-30", "10:00", 1, "no existe"),
        ]
        for nombre, sala, fecha, hora, duracion, palabra in rechazos:
            resultado, error, texto = self.consultar_disponibilidad(sala, fecha, hora, duracion)
            if resultado is not None or not error or palabra not in error[2]:
                problemas.append(f"{nombre}: error={error}, texto='{texto}'")
        self.assertEqual(problemas, [])

    def test_CP_RF08_04_la_consulta_no_modifica_la_informacion(self):
        existente = self.preparar_reserva_existente()
        self.assertEqual(existente.identificador, "R0001")
        self.salir()
        antes = os.stat(self.ruta)
        self.abrir()
        listado_antes = self.lista()
        eventos_antes = self.persistencia.conexion.execute("SELECT COUNT(*) FROM auditoria").fetchone()[0]
        for sala, hora in (("S01", "10:00"), ("S02", "10:00"), ("S99", "10:00")):
            self.consultar_disponibilidad(sala, "2026-12-15", hora, 1)
        self.assertEqual(self.lista(), listado_antes)
        eventos_despues = self.persistencia.conexion.execute("SELECT COUNT(*) FROM auditoria").fetchone()[0]
        self.assertEqual(eventos_despues, eventos_antes)
        self.salir()
        despues = os.stat(self.ruta)
        self.assertEqual((despues.st_size, despues.st_mtime_ns), (antes.st_size, antes.st_mtime_ns),
                         "El archivo de la base de datos cambió de tamaño o de fecha de modificación")
        self.abrir()
        resultado, mensaje = self.intentar_reserva(A, "S02", "2026-12-15", "10:00", 1, 1)
        self.assertTrue(resultado)
        self.assertIn("R0002", mensaje[2])


# Casos RF-15
class CP_RF15(CasoReservaciones):
    """Reloj de la prueba: 2026-10-12 10:00 (el caso pide ejecutarlo entre las 09:00 y las 14:59)."""

    ahora = datetime(2026, 10, 12, 10, 0)
    PREVIO = datetime(2026, 10, 12, 7, 0)  # reloj para guardar la reservación que "ya pasó"

    def preparar_panel(self):
        """Guarda las 6 reservaciones del caso CP-RF15-01.

        Se guardan en desorden (3, 1, 4, 6, 2, 5) para que el orden por fecha y hora del panel no dependa
        del orden de los ID. Devuelve {número de reservación del caso: ID asignado}.
        """
        r = self.PREVIO
        datos = {
            1: (A, "S01", "2026-10-12", "08:00", 1, 2),   # hoy, ya pasó
            2: (B, "S02", "2026-10-12", "11:00", 1, 2),   # hoy, dentro de 1 hora
            3: (A, "S02", "2026-10-12", "13:00", 1, 2),   # hoy, dentro de 3 horas
            4: (B, "S03", "2026-10-13", "10:00", 1, 2),   # mañana 10:00
            5: (A, "S01", "2026-10-14", "14:00", 1, 2),   # pasado mañana 14:00 (se cancela)
            6: (B, "S05", "2026-10-12", "12:00", 1, 1),   # hoy, dentro de 2 horas (se cancela)
        }
        self.num = {n: self.preparar(*datos[n], reloj=r).identificador for n in (3, 1, 4, 6, 2, 5)}
        self.cancelar_directo(self.num[5])
        self.cancelar_directo(self.num[6])
        self.fijar_reloj(self.ahora)
        return self.num

    def test_CP_RF15_01_reservaciones_del_dia_proximas_y_ocupacion(self):
        n = self.preparar_panel()
        panel = self.panel()
        problemas = []
        hoy, proximas = self.ids(self.filas(panel.tabla_hoy)), self.ids(self.filas(panel.tabla_proximas))
        if hoy != [n[1], n[2], n[3]]:
            problemas.append(f"Reservaciones de hoy: se esperaba {[n[1], n[2], n[3]]} (1, 2 y 3) y se obtuvo {hoy}")
        if proximas != [n[2], n[3], n[4]]:
            problemas.append(f"Próximas: se esperaba {[n[2], n[3], n[4]]} (2, 3 y 4) y se obtuvo {proximas}")
        esperada = {"S01": 1, "S02": 2, "S03": 0, "S04": 0, "S05": 0}
        if self.ocupacion(panel) != esperada:
            problemas.append(f"Ocupación: se esperaba {esperada} y se obtuvo {self.ocupacion(panel)}")
        self.assertEqual(problemas, [])

    def test_CP_RF15_02_actualizacion_despues_de_crear_modificar_y_cancelar(self):
        n = self.preparar_panel()
        problemas = []
        # Crear: B009876543, S03, hoy dentro de 4 horas (14:00), 1 hora, 1 persona.
        resultado, _ = self.intentar_reserva(B, "S03", "2026-10-12", "14:00", 1, 1)
        panel = self.panel()
        hoy, proximas = self.ids(self.filas(panel.tabla_hoy)), self.ids(self.filas(panel.tabla_proximas))
        if not resultado or "R0007" not in hoy or "R0007" not in proximas or self.ocupacion(panel)["S03"] != 1:
            problemas.append(f"Después de crear: hoy={hoy}, próximas={proximas}, ocupación={self.ocupacion(panel)}")
        # Modificar la reservación 2 a la sala S03, mismo horario.
        modificada, _ = self.modificar(n[2], sala="S03")
        panel = self.panel()
        sala_r2 = next((f[2] for f in self.filas(panel.tabla_hoy) if f[0] == n[2]), None)
        ocupacion = self.ocupacion(panel)
        if not modificada or sala_r2 != "S03" or (ocupacion["S02"], ocupacion["S03"]) != (1, 2):
            problemas.append(f"Después de modificar: sala de la reservación 2={sala_r2}, ocupación={ocupacion}")
        # Cancelar la reservación 3.
        self.cancelar(n[3])
        panel = self.panel()
        hoy, proximas = self.ids(self.filas(panel.tabla_hoy)), self.ids(self.filas(panel.tabla_proximas))
        ocupacion = self.ocupacion(panel)
        if n[3] in hoy or n[3] in proximas or ocupacion["S02"] != 0:
            problemas.append(f"Después de cancelar: hoy={hoy}, próximas={proximas}, ocupación={ocupacion}")
        for nombre, tabla in (("hoy", panel.tabla_hoy), ("próximas", panel.tabla_proximas)):
            if not self.sin_repetidas(self.filas(tabla)):
                problemas.append(f"Reservaciones repetidas en '{nombre}': {self.ids(self.filas(tabla))}")
        self.assertEqual(problemas, [])

    def test_CP_RF15_03_filtros_por_fecha_sala_y_estado(self):
        n = self.preparar_panel()
        panel = self.panel()
        casos = [
            ("fecha (mañana)", dict(fecha="2026-10-13"), [n[4]]),
            ("sala S02", dict(sala="S02"), [n[2], n[3]]),
            ("estado cancelada", dict(estado="cancelada"), [n[5], n[6]]),
            ("combinados (hoy, S02, activa)", dict(fecha="2026-10-12", sala="S02", estado="activa"),
             [n[2], n[3]]),
        ]
        problemas = []
        for nombre, filtros, esperado in casos:
            self.clic(panel.limpiar_filtros)
            panel.filtro_fecha.set(filtros.get("fecha", ""))
            panel.filtro_sala.set(filtros.get("sala", "Todas"))
            panel.filtro_estado.set(filtros.get("estado", "Todos"))
            self.clic(panel.actualizar)
            obtenido = sorted(self.ids(self.filas(panel.tabla_filtrada)))
            if obtenido != sorted(esperado):
                problemas.append(f"{nombre}: se esperaba {esperado} y se obtuvo {obtenido}")
        self.assertEqual(problemas, [])

    def test_CP_RF15_04_estado_vacio_del_panel(self):
        problemas = []
        panel = self.panel()
        mensajes = {c: panel.mensajes[c].cget("text") for c in ("hoy", "proximas", "filtradas")}
        if not mensajes["hoy"].startswith("No hay") or not mensajes["proximas"].startswith("No hay"):
            problemas.append(f"Sin reservaciones, mensajes del panel: {mensajes}")
        if set(self.ocupacion(panel).values()) != {0}:
            problemas.append(f"Sin reservaciones, la ocupación debía ser 0: {self.ocupacion(panel)}")
        # Segunda parte: con reservaciones guardadas y un filtro sin resultados (dentro de 3 días).
        self.preparar_panel()
        panel = self.panel()
        self.msg.limpiar()
        panel.filtro_fecha.set("2026-10-15")
        self.clic(panel.actualizar)
        texto = panel.mensajes["filtradas"].cget("text")
        if self.filas(panel.tabla_filtrada) or "No hay" not in texto:
            problemas.append(f"Filtro sin resultados: filas={self.filas(panel.tabla_filtrada)}, mensaje='{texto}'")
        if self.msg.ultimo("showerror"):
            problemas.append(f"El filtro sin resultados mostró un error: {self.msg.ultimo('showerror')}")
        self.assertEqual(problemas, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
