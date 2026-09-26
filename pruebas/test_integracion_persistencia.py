import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from solucion.auditoria import Auditoria
from solucion.contratos import ErrorPersistencia
from solucion.estudiantes import ServicioEstudiantes
from solucion.persistencia import PersistenciaSQLite
from solucion.validaciones import ErrorValidacion


class IntegracionTest(unittest.TestCase):
    # Verifica el ciclo de registro, inactivación, reactivación y reinicio.
    def test_escenario_estudiante_auditoria_y_reinicio(self):
        estudiante = self.alta()
        self.servicio.modificar(estudiante.carne, "María Núñez", estudiante.correo, "inactivo")
        with self.persistencia.transaccion() as sesion:
            with self.assertRaises(ErrorValidacion):
                self.servicio.exigir_activo(sesion, estudiante.carne)
        self.servicio.modificar(estudiante.carne, "María Núñez", estudiante.correo, "activo")
        self.persistencia.cerrar()
        self.persistencia = PersistenciaSQLite(self.ruta)
        self.servicio = ServicioEstudiantes(self.persistencia)
        with self.persistencia.lectura() as sesion:
            recuperado = self.servicio.exigir_activo(sesion, estudiante.carne)
        self.assertEqual(recuperado.nombre, "María Núñez")
        self.assertEqual(
            [evento.accion for evento in self.eventos()],
            ["modificacion", "modificacion", "creacion"],
        )

    # Comprueba que una falla de auditoría no impida una operación válida posterior.
    def test_recuperacion_despues_de_fallo_de_auditoria(self):
        self.persistencia.conexion.execute(
            "CREATE TRIGGER bloquear BEFORE INSERT ON auditoria "
            "BEGIN SELECT RAISE(ABORT,'fallo'); END"
        )
        with self.assertRaises(ErrorPersistencia):
            self.alta()
        self.persistencia.conexion.execute("DROP TRIGGER bloquear")
        estudiante = self.alta()
        self.assertEqual(self.servicio.consultar(), [estudiante])
        self.assertEqual(len(self.eventos()), 1)

    # Prepara los recursos necesarios para una prueba independiente.
    def setUp(self):
        self.directorio_temporal = tempfile.TemporaryDirectory()
        self.ruta = Path(self.directorio_temporal.name) / "test.sqlite3"
        self.persistencia = PersistenciaSQLite(self.ruta)
        self.auditoria = Auditoria(lambda: datetime(2026, 9, 24, 14, 30, tzinfo=timezone.utc))
        self.servicio = ServicioEstudiantes(self.persistencia, self.auditoria)

    # Libera los recursos utilizados durante la prueba.
    def tearDown(self):
        self.persistencia.cerrar()
        self.directorio_temporal.cleanup()

    # Registra un estudiante con datos válidos de prueba.
    def alta(self, carne="A123456789", nombre="María Ñúñez"):
        return self.servicio.registrar(carne, nombre, "maria@universidad.ac.cr")

    # Consulta la auditoría generada durante la prueba.
    def eventos(self):
        return self.auditoria.consultar(self.persistencia)

    # Comprueba registro normalizado y activo.
    def test_rf02_registro_normalizado_y_activo(self):
        estudiante = self.servicio.registrar(" a123456789 ", " María Ñúñez ", " maria@u.ac.cr ")
        self.assertEqual((estudiante.carne, estudiante.nombre, estudiante.correo, estudiante.estado),
                         ("a123456789", "María Ñúñez", "maria@u.ac.cr", "activo"))
        self.assertEqual(self.servicio.consultar(), [estudiante])

    # Comprueba duplicado sin distinguir capitalización sin evento.
    def test_rf02_duplicado_case_insensitive_sin_evento(self):
        self.alta()
        with self.assertRaisesRegex(ErrorValidacion, "Carné"):
            self.alta("a123456789")
        self.assertEqual(len(self.servicio.consultar()), 1)
        self.assertEqual(len(self.eventos()), 1)

    # Comprueba duplicado entre conexiones.
    def test_rf02_duplicado_entre_conexiones(self):
        otra = PersistenciaSQLite(self.ruta)
        try:
            self.alta()
            with self.assertRaises(ErrorValidacion):
                ServicioEstudiantes(otra).registrar("a123456789", "Ana", "a@b.c")
        finally:
            otra.cerrar()
        self.assertEqual(len(self.eventos()), 1)

    # Comprueba fallo validación no escribe.
    def test_rf02_fallo_validacion_no_escribe(self):
        for args in (("A1", "Ana", "a@b.c"), ("A123456789", "A", "a@b.c"),
                     ("A123456789", "Ana", "abc")):
            with self.subTest(args=args), self.assertRaises(ErrorValidacion):
                self.servicio.registrar(*args)
        self.assertEqual(self.servicio.consultar(), [])
        self.assertEqual(self.eventos(), [])

    # Comprueba vacio orden y estados.
    def test_rf03_vacio_orden_y_estados(self):
        self.assertEqual(self.servicio.consultar(), [])
        self.alta(nombre="Zoe")
        self.alta("B123456789", "álvaro")
        self.alta("C123456789", "Beatriz")
        self.servicio.modificar("B123456789", "álvaro", "a@b.c", "inactivo")
        self.assertEqual([estudiante.nombre for estudiante in self.servicio.consultar()], ["álvaro", "Beatriz", "Zoe"])
        self.assertEqual(self.servicio.consultar()[0].estado, "inactivo")

    # Comprueba carne inmutable y reactivacion.
    def test_rf11_carne_inmutable_y_reactivacion(self):
        self.alta()
        estudiante = self.servicio.modificar("a123456789", "Ana", "ana@u.ac.cr", "inactivo")
        self.assertEqual(estudiante.carne, "A123456789")
        with self.persistencia.transaccion() as sesion:
            with self.assertRaisesRegex(ErrorValidacion, "inactivo"):
                self.servicio.exigir_activo(sesion, "a123456789")
        self.servicio.modificar(estudiante.carne, estudiante.nombre, estudiante.correo, "activo")
        with self.persistencia.transaccion() as sesion:
            self.assertEqual(self.servicio.exigir_activo(sesion, estudiante.carne).estado, "activo")
        self.assertEqual(len(self.eventos()), 3)

    # Comprueba inexistente.
    def test_rn01_inexistente(self):
        with self.persistencia.transaccion() as sesion:
            with self.assertRaisesRegex(ErrorValidacion, "no existe"):
                self.servicio.exigir_activo(sesion, "A123456789")

    # Comprueba rechazo conserva original.
    def test_rf11_rechazo_conserva_original(self):
        original = self.alta()
        for datos in (("A", "a@b.c", "activo"), ("Ana", "abc", "activo"),
                      ("Ana", "a@b.c", "otro")):
            with self.subTest(datos=datos), self.assertRaises(ErrorValidacion):
                self.servicio.modificar(original.carne, *datos)
        self.assertEqual(self.servicio.consultar(), [original])
        self.assertEqual(len(self.eventos()), 1)

    # Comprueba inexistente.
    def test_rf11_inexistente(self):
        with self.assertRaises(ErrorValidacion):
            self.servicio.modificar("A123456789", "Ana", "a@b.c", "activo")
        self.assertEqual(self.eventos(), [])

    # Comprueba guardado sin cambios no genera modificacion.
    def test_rf11_noop_no_genera_modificacion(self):
        estudiante = self.alta()
        self.servicio.modificar(estudiante.carne, estudiante.nombre, estudiante.correo, estudiante.estado)
        self.assertEqual(len(self.eventos()), 1)

    # Comprueba preserva historial referenciado.
    def test_rf11_preserva_historial_referenciado(self):
        self.alta()
        # Tabla mínima de un módulo consumidor, solo fixture, no implementación RF-05.
        with self.persistencia.transaccion() as sesion:
            sesion.conexion.execute("CREATE TABLE reservas_prueba(id TEXT PRIMARY KEY, carne TEXT REFERENCES estudiantes(carne))")
            sesion.conexion.execute("INSERT INTO reservas_prueba VALUES ('R0001','A123456789')")
        self.servicio.modificar("A123456789", "Ana", "a@b.c", "inactivo")
        with self.persistencia.lectura() as sesion:
            self.assertEqual(sesion.conexion.execute("SELECT * FROM reservas_prueba").fetchall(),
                             [("R0001", "A123456789")])

    # Comprueba campos evento.
    def test_rf17_campos_evento(self):
        self.alta()
        evento = self.eventos()[0]
        self.assertEqual((evento.fecha_hora, evento.accion, evento.entidad, evento.identificador),
                         ("2026-09-24T14:30:00+00:00", "creacion", "estudiante", "A123456789"))

    # Comprueba otros modulos y cancelacion.
    def test_rf17_otros_modulos_y_cancelacion(self):
        with self.persistencia.transaccion() as sesion:
            for accion, entidad, identificador in (("creacion", "sala", "S06"),
                    ("modificacion", "reservacion", "R0001"), ("cancelacion", "reservacion", "R0002")):
                self.auditoria.registrar(sesion, accion, entidad, identificador)
        self.assertEqual([evento.accion for evento in self.eventos()], ["cancelacion", "modificacion", "creacion"])

    # Comprueba error despues de evento revierte todo.
    def test_rf17_error_despues_de_evento_revierte_todo(self):
        with self.assertRaises(RuntimeError):
            with self.persistencia.transaccion() as sesion:
                self.auditoria.registrar(sesion, "creacion", "sala", "S06")
                raise RuntimeError("Fallo simulado en módulo consumidor")
        self.assertEqual(self.eventos(), [])

    # Comprueba fallo auditoria revierte alta.
    def test_rf17_fallo_auditoria_revierte_alta(self):
        self.persistencia.conexion.execute("CREATE TRIGGER bloquear BEFORE INSERT ON auditoria BEGIN SELECT RAISE(ABORT,'fallo'); END")
        with self.assertRaises(ErrorPersistencia):
            self.alta()
        self.assertEqual(self.servicio.consultar(), [])
        self.assertEqual(self.eventos(), [])

    # Comprueba fallo auditoria revierte edicion.
    def test_rf17_fallo_auditoria_revierte_edicion(self):
        original = self.alta()
        self.persistencia.conexion.execute("CREATE TRIGGER bloquear BEFORE INSERT ON auditoria BEGIN SELECT RAISE(ABORT,'fallo'); END")
        with self.assertRaises(ErrorPersistencia):
            self.servicio.modificar(original.carne, "Ana", "a@b.c", "inactivo")
        self.assertEqual(self.servicio.consultar(), [original])
        self.assertEqual(len(self.eventos()), 1)

    # Comprueba acción inválida.
    def test_rf17_accion_invalida(self):
        for args in (("consulta", "sala", "S01"), ("creacion", "", "S01"), ("creacion", "sala", "")):
            with self.subTest(args=args), self.assertRaises(ErrorValidacion):
                with self.persistencia.transaccion() as sesion:
                    self.auditoria.registrar(sesion, *args)
        self.assertEqual(self.eventos(), [])

    # Verifica reinicio conserva datos y auditoria sin duplicados.
    def test_reinicio_conserva_datos_y_auditoria_sin_duplicados(self):
        original = self.alta()
        self.persistencia.cerrar()
        self.persistencia = PersistenciaSQLite(self.ruta)
        self.servicio = ServicioEstudiantes(self.persistencia)
        self.assertEqual(self.servicio.consultar(), [original])
        self.assertEqual(len(self.eventos()), 1)

    # Comprueba cierre durante transaccion rechazado.
    def test_rf10_cierre_durante_transaccion_rechazado(self):
        with self.persistencia.transaccion():
            with self.assertRaises(ErrorPersistencia):
                self.persistencia.cerrar()
        self.alta()

    # Verifica sql parametrizado.
    def test_sql_parametrizado(self):
        nombre = "Ana'); DROP TABLE estudiantes; --"
        self.alta(nombre=nombre)
        self.assertEqual(self.servicio.consultar()[0].nombre, nombre)

    # Verifica esquema ajeno no se modifica.
    def test_esquema_ajeno_no_se_modifica(self):
        ajena = Path(self.directorio_temporal.name) / "ajena.sqlite3"
        conexion = sqlite3.connect(ajena)
        conexion.execute("CREATE TABLE otra(id INTEGER)")
        conexion.commit()
        conexion.close()
        original = ajena.read_bytes()
        with self.assertRaises(ErrorPersistencia):
            PersistenciaSQLite(ajena)
        self.assertEqual(ajena.read_bytes(), original)

    # Verifica base corrupta error controlado.
    def test_bd_corrupta_error_controlado(self):
        ruta = Path(self.directorio_temporal.name) / "corrupta.sqlite3"
        ruta.write_bytes(b"esto no es SQLite")
        with self.assertRaises(ErrorPersistencia):
            PersistenciaSQLite(ruta)

    # Verifica el rechazo de transacciones anidadas.
    def test_transacciones_anidadas_rechazadas(self):
        with self.persistencia.transaccion():
            with self.assertRaises(ErrorPersistencia):
                with self.persistencia.transaccion():
                    pass
        self.alta()
