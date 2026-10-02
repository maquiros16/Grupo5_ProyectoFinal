"""Pruebas del motor de reglas (RN-01 a RN-11) sin base de datos ni interfaz."""
import unittest
from datetime import date, datetime

from solucion import reglas
from solucion.contratos import Estudiante, Reservacion, Sala
from solucion.validaciones import ErrorValidacion


AHORA = datetime(2026, 9, 28, 10, 30)
HOY = AHORA.date()
ACTIVO = Estudiante("D007654321", "Laura Vargas", "laura@universidad.ac.cr")
SALA = Sala("S01", "Sala Biblioteca 1", 4)


# Crea una reservación de prueba con valores por defecto.
def reserva(identificador="R0001", sala="S01", fecha="2026-09-30", inicio="10:00", duracion=1,
            estado="activa", carne="D007654321"):
    return Reservacion(identificador, carne, sala, fecha, inicio, duracion, 2, estado)


class ReglasTest(unittest.TestCase):
    # Comprueba estudiante inexistente, inactivo y activo.
    def test_rn01_estudiante(self):
        with self.assertRaisesRegex(ErrorValidacion, "no existe"):
            reglas.validar_estudiante(None)
        inactivo = Estudiante("D007654321", "Laura Vargas", "laura@universidad.ac.cr", "inactivo")
        with self.assertRaisesRegex(ErrorValidacion, "inactivo"):
            reglas.validar_estudiante(inactivo)
        self.assertEqual(reglas.validar_estudiante(ACTIVO), ACTIVO)

    # Comprueba formato, fecha inexistente, límite de ayer y hoy.
    def test_rn02_fecha(self):
        for valor in ("", "28/09/2026", "2026-9-28", "20260928", None, 20260928):
            with self.subTest(valor=valor), self.assertRaises(ErrorValidacion):
                reglas.validar_fecha(valor, HOY)
        with self.assertRaisesRegex(ErrorValidacion, "no existe"):
            reglas.validar_fecha("2026-02-30", HOY)
        with self.assertRaisesRegex(ErrorValidacion, "anterior"):
            reglas.validar_fecha("2026-09-27", HOY)
        self.assertEqual(reglas.validar_fecha(" 2026-09-28 ", HOY), date(2026, 9, 28))
        self.assertEqual(reglas.validar_fecha("2026-09-29", HOY), date(2026, 9, 29))

    # Comprueba reservas de hoy con hora pasada, actual y futura.
    def test_rn03_inicio_despues_de_la_hora_actual(self):
        with self.assertRaises(ErrorValidacion):
            reglas.validar_inicio_futuro(HOY, 10, AHORA)
        with self.assertRaises(ErrorValidacion):
            reglas.validar_inicio_futuro(HOY, 11, datetime(2026, 9, 28, 11, 0))
        reglas.validar_inicio_futuro(HOY, 11, AHORA)
        reglas.validar_inicio_futuro(date(2026, 9, 29), 8, AHORA)

    # Comprueba formato de 24 horas y hora completa.
    def test_rn04_hora(self):
        for valor in ("", "9:00", "09:30", "09:01", "24:00", "12:60", "9 am", "0900", None, 9):
            with self.subTest(valor=valor), self.assertRaises(ErrorValidacion):
                reglas.validar_hora(valor)
        self.assertEqual(reglas.validar_hora(" 09:00 "), 9)
        self.assertEqual(reglas.validar_hora("19:00"), 19)

    # Comprueba los valores límite del horario.
    def test_rn05_horario_limites(self):
        for hora, duracion in ((7, 1), (19, 2), (20, 1)):
            with self.subTest(hora=hora, duracion=duracion), self.assertRaises(ErrorValidacion):
                reglas.validar_horario(hora, duracion)
        for hora, duracion in ((8, 1), (8, 2), (18, 2), (19, 1)):
            with self.subTest(hora=hora, duracion=duracion):
                reglas.validar_horario(hora, duracion)

    # Comprueba duraciones válidas e inválidas.
    def test_rn06_duracion(self):
        for valor in (0, 3, -1, "1.5", 1.5, True, "", "dos", None):
            with self.subTest(valor=valor), self.assertRaises(ErrorValidacion):
                reglas.validar_duracion(valor)
        self.assertEqual(reglas.validar_duracion(1), 1)
        self.assertEqual(reglas.validar_duracion(" 2 "), 2)

    # Comprueba cantidad cero, decimal, capacidad exacta y excedida.
    def test_rn07_cantidad(self):
        for valor in (0, -1, 5, "2.0", 2.0, "", None, True):
            with self.subTest(valor=valor), self.assertRaises(ErrorValidacion):
                reglas.validar_cantidad(valor, 4)
        self.assertEqual(reglas.validar_cantidad("4", 4), 4)
        self.assertEqual(reglas.validar_cantidad(1, 4), 1)

    # Comprueba sala inexistente, fuera de servicio y disponible.
    def test_rn08_sala(self):
        with self.assertRaisesRegex(ErrorValidacion, "no existe"):
            reglas.validar_sala(None)
        with self.assertRaisesRegex(ErrorValidacion, "fuera de servicio"):
            reglas.validar_sala(Sala("S04", "Sala multimedia", 8, "fuera_de_servicio"))
        self.assertEqual(reglas.validar_sala(SALA), SALA)

    # Comprueba el cálculo de la hora de finalización a partir de la duración.
    def test_hora_fin(self):
        self.assertEqual(reglas.hora_fin(reserva(inicio="18:00", duracion=2)), "20:00")
        self.assertEqual(reglas.hora_fin(reserva(inicio="08:00", duracion=1)), "09:00")

    # Comprueba la tabla de decisión de superposición del enunciado.
    def test_rn09_rn10_tabla_de_superposicion(self):
        casos = (
            ("10:00", "11:00", "10:00", "11:00", True),   # Conflicto total.
            ("10:00", "12:00", "11:00", "12:00", True),   # Conflicto parcial.
            ("10:00", "12:00", "09:00", "11:00", True),   # Conflicto parcial al inicio.
            ("10:00", "12:00", "10:00", "11:00", True),   # Nueva dentro de la existente.
            ("10:00", "11:00", "09:00", "12:00", True),   # Nueva envuelve a la existente.
            ("10:00", "11:00", "11:00", "12:00", False),  # Consecutiva después.
            ("10:00", "12:00", "12:00", "13:00", False),  # Consecutiva después.
            ("10:00", "11:00", "09:00", "10:00", False),  # Consecutiva antes.
        )
        for inicio_e, fin_e, inicio_n, fin_n, esperado in casos:
            with self.subTest(existente=(inicio_e, fin_e), nueva=(inicio_n, fin_n)):
                self.assertEqual(reglas.hay_superposicion(inicio_n, fin_n, inicio_e, fin_e), esperado)

    # Comprueba que solo bloqueen reservas activas de la misma sala y fecha.
    def test_rn09_rn12_conflictos_solo_activos_misma_sala_y_fecha(self):
        horario = reglas.Horario("2026-09-30", "10:00", "11:00", 1)
        existentes = [
            reserva("R0001", estado="cancelada"),
            reserva("R0002", sala="S02"),
            reserva("R0003", fecha="2026-10-01"),
        ]
        self.assertEqual(reglas.buscar_conflictos("S01", horario, existentes), ())
        existentes.append(reserva("R0004", inicio="09:00", duracion=2))
        conflictos = reglas.buscar_conflictos("S01", horario, existentes)
        self.assertEqual([r.identificador for r in conflictos], ["R0004"])
        with self.assertRaisesRegex(ErrorValidacion, r"R0004 \(09:00-11:00\)"):
            reglas.validar_sin_conflictos("S01", horario, existentes)
        reglas.validar_sin_conflictos("S01", horario, existentes, excluir_id="R0004")

    # Comprueba que tres reservas vigentes bloqueen y que pasadas y canceladas no cuenten.
    def test_rn11_limite_por_estudiante(self):
        vigentes = [reserva(f"R000{n}", fecha=f"2026-10-0{n}") for n in range(1, 3)]
        otras = [
            reserva("R0010", fecha="2026-09-27"),                   # Reserva pasada.
            reserva("R0011", fecha="2026-09-28", inicio="09:00"),   # Reserva que terminó hoy a las 10:00.
            reserva("R0012", estado="cancelada"),
        ]
        reglas.validar_limite_estudiante(vigentes + otras, AHORA)
        en_curso = reserva("R0003", fecha="2026-09-28", inicio="10:00", duracion=2)  # Reserva presente.
        with self.assertRaisesRegex(ErrorValidacion, "3 reservaciones"):
            reglas.validar_limite_estudiante(vigentes + otras + [en_curso], AHORA)
        reglas.validar_limite_estudiante(vigentes + [en_curso], AHORA, excluir_id="R0003")

    # Cada ocurrencia de una serie cuenta como una reserva independiente.
    def test_rn11_cada_ocurrencia_cuenta_por_separado(self):
        ocurrencias = [
            reserva(f"R000{n}", fecha=f"2026-10-0{n}")
            for n in range(1, 5)
        ]
        series = {r.identificador: "S0001" for r in ocurrencias}

        self.assertEqual(
            reglas.contar_activas_vigentes(
                ocurrencias, AHORA, series_por_reserva=series
            ),
            4,
        )

        individuales = [
            reserva("R0010", fecha="2026-10-10"),
            reserva("R0011", fecha="2026-10-11"),
        ]
        self.assertEqual(
            reglas.contar_activas_vigentes(
                ocurrencias + individuales,
                AHORA,
                series_por_reserva=series,
            ),
            6,
        )

        with self.assertRaisesRegex(ErrorValidacion, "3 reservaciones"):
            reglas.validar_limite_estudiante(
                ocurrencias, AHORA, series_por_reserva=series
            )

        self.assertEqual(
            reglas.contar_activas_vigentes(
                ocurrencias,
                AHORA,
                excluir_id="R0001",
                series_por_reserva=series,
            ),
            3,
        )
            
    # Comprueba el flujo completo y el orden de los rechazos.
    def test_validar_reservacion_completa(self):
        solicitud = reglas.validar_reservacion(
            ACTIVO, SALA, "2026-09-30", "18:00", "2", "4", [reserva()], [], AHORA
        )
        self.assertEqual(solicitud, reglas.Solicitud("2026-09-30", "18:00", "20:00", 2, 4))
        with self.assertRaisesRegex(ErrorValidacion, "Carné"):
            reglas.validar_reservacion(None, None, "", "", "", "", [], [], AHORA)
        with self.assertRaisesRegex(ErrorValidacion, "Sala"):
            reglas.validar_reservacion(ACTIVO, None, "", "", "", "", [], [], AHORA)
        with self.assertRaisesRegex(ErrorValidacion, "ya está reservada"):
            reglas.validar_reservacion(ACTIVO, SALA, "2026-09-30", "10:00", 1, 2, [reserva()], [], AHORA)

    # Comprueba que la disponibilidad informa conflictos sin lanzar error.
    def test_rf08_evaluar_disponibilidad(self):
        libre = reglas.evaluar_disponibilidad(SALA, "2026-09-30", "11:00", 1, [reserva()], AHORA)
        self.assertTrue(libre.disponible)
        self.assertEqual(libre.horario.hora_fin, "12:00")
        ocupada = reglas.evaluar_disponibilidad(SALA, "2026-09-30", "09:00", 2, [reserva()], AHORA)
        self.assertFalse(ocupada.disponible)
        self.assertEqual([r.identificador for r in ocupada.conflictos], ["R0001"])
        with self.assertRaises(ErrorValidacion):
            reglas.evaluar_disponibilidad(SALA, "2026-09-30", "19:00", 2, [], AHORA)


if __name__ == "__main__":
    unittest.main()
