import unittest
from datetime import datetime, timezone
from unittest.mock import Mock

from solucion.auditoria import Auditoria
from solucion.validaciones import ErrorValidacion


class AuditoriaTest(unittest.TestCase):
    # Comprueba registro usa fecha y sesion recibidas.
    def test_rf17_registro_usa_fecha_y_sesion_recibidas(self):
        sesion = Mock()
        fecha = datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)
        auditoria = Auditoria(reloj=lambda: fecha)
        auditoria.registrar(sesion, "creacion", " sala ", " S01 ")
        sesion.agregar_evento.assert_called_once_with(
            "2026-09-25T12:00:00+00:00", "creacion", "sala", "S01"
        )

    # Comprueba rechazo no invoca persistencia.
    def test_rf17_rechazo_no_invoca_persistencia(self):
        sesion = Mock()
        for accion, entidad, identificador in (
            ("consulta", "sala", "S01"), ("creacion", "", "S01"),
            ("creacion", "sala", None),
        ):
            with self.subTest(accion=accion, entidad=entidad, identificador=identificador):
                with self.assertRaises(ErrorValidacion):
                    Auditoria().registrar(sesion, accion, entidad, identificador)
        sesion.agregar_evento.assert_not_called()
