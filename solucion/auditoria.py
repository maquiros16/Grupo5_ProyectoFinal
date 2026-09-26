"""RF-17: API reutilizable dentro de la transacción de cualquier módulo."""
from datetime import datetime
from .validaciones import normalizar_texto, ErrorValidacion


class Auditoria:
    # Configura el reloj utilizado para fechar las acciones.
    def __init__(self, reloj=None):
        self.reloj = reloj or (lambda: datetime.now().astimezone())

    # Registra una acción válida utilizando la sesión y el reloj recibidos.
    def registrar(self, sesion, accion, entidad, identificador):
        if accion not in ("creacion", "modificacion", "cancelacion"):
            raise ErrorValidacion("Acción de auditoría no válida.")
        entidad = normalizar_texto(entidad, "Entidad")
        identificador = normalizar_texto(str(identificador), "Identificador") if identificador is not None else ""
        if not entidad or not identificador:
            raise ErrorValidacion("Auditoría: entidad e identificador son obligatorios.")
        sesion.agregar_evento(self.reloj().isoformat(timespec="seconds"), accion, entidad, identificador)

    # Recupera los registros disponibles para consulta.
    @staticmethod
    def consultar(persistencia):
        with persistencia.lectura() as sesion:
            return sesion.listar_eventos()
