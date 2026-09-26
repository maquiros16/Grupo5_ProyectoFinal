import unittest
from unittest.mock import Mock
from solucion.cierre import CierreControlado, ParticipanteCierre
from solucion.contratos import ErrorPersistencia


class CierreTest(unittest.TestCase):
    # Configura los colaboradores del cierre con respuestas controladas.
    def preparar(self, pendiente=True, guardar=True):
        self.estado = pendiente
        self.recursos, self.finalizar = Mock(), Mock()
        self.cierre = CierreControlado(self.recursos, self.finalizar)
        # Simula el guardado del formulario y actualiza su estado pendiente.
        def salvar():
            if guardar:
                self.estado = False
            return guardar
        self.salvar = Mock(side_effect=salvar)
        self.descartar = Mock(side_effect=lambda: setattr(self, "estado", False))
        self.cierre.agregar(ParticipanteCierre("Estudiantes", lambda: self.estado, self.salvar, self.descartar))

    # Comprueba sin pendientes cierra sin pregunta.
    def test_rf10_sin_pendientes_cierra_sin_pregunta(self):
        self.preparar(False)
        decidir = Mock()
        self.assertTrue(self.cierre.solicitar(decidir))
        decidir.assert_not_called()
        self.finalizar.assert_called_once()
        self.assertTrue(self.cierre.solicitar(decidir))
        self.recursos.assert_called_once()

    # Comprueba cancelar permanece abierta.
    def test_rf10_cancelar_permanece_abierta(self):
        self.preparar()
        self.assertFalse(self.cierre.solicitar(lambda _: "cancelar"))
        self.recursos.assert_not_called()
        self.assertTrue(self.estado)

    # Comprueba guardar antes cerrar.
    def test_rf10_guardar_antes_cerrar(self):
        self.preparar()
        self.assertTrue(self.cierre.solicitar(lambda _: "guardar"))
        self.salvar.assert_called_once()
        self.recursos.assert_called_once()
        self.assertFalse(self.estado)

    # Comprueba descartar borrador.
    def test_rf10_descartar_borrador(self):
        self.preparar()
        self.assertTrue(self.cierre.solicitar(lambda _: "descartar"))
        self.descartar.assert_called_once()
        self.salvar.assert_not_called()

    # Comprueba guardado fallido no cierra.
    def test_rf10_guardado_fallido_no_cierra(self):
        self.preparar(guardar=False)
        self.assertFalse(self.cierre.solicitar(lambda _: "guardar"))
        self.recursos.assert_not_called()

    # Comprueba error cerrar no destruye.
    def test_rf10_error_cerrar_no_destruye(self):
        self.preparar(False)
        self.recursos.side_effect = ErrorPersistencia("Fallo simulado")
        with self.assertRaises(ErrorPersistencia):
            self.cierre.solicitar(lambda _: "guardar")
        self.finalizar.assert_not_called()
        self.assertFalse(self.cierre.finalizado)

    # Comprueba varios modulos.
    def test_rf10_varios_modulos(self):
        self.preparar()
        segundo = Mock(return_value=False)
        self.cierre.agregar(ParticipanteCierre("Reservaciones", lambda: True, segundo, Mock()))
        self.assertFalse(self.cierre.solicitar(lambda _: "guardar"))
        segundo.assert_called_once()
        self.finalizar.assert_not_called()
