"""RF-10: coordinador reutilizable, independiente de Tkinter."""
from dataclasses import dataclass
from typing import Callable


@dataclass
class ParticipanteCierre:
    nombre: str
    pendiente: Callable[[], bool]
    guardar: Callable[[], bool]
    descartar: Callable[[], None]


class CierreControlado:
    # Configura los recursos y formularios que participan en el cierre.
    def __init__(self, cerrar_recursos, finalizar):
        self.participantes = []
        self.cerrar_recursos = cerrar_recursos
        self.finalizar = finalizar
        self.finalizado = False

    # Incorpora un formulario al control de cambios pendientes.
    def agregar(self, participante):
        self.participantes.append(participante)

    # Resuelve los borradores antes de cerrar los recursos y la ventana.
    def solicitar(self, decidir):
        """decidir(nombres) devuelve guardar, descartar o cancelar.

        Descartar afecta solamente borradores de interfaz, nunca datos confirmados.
        Si falla cualquier paso, la ventana permanece abierta.
        """
        if self.finalizado:
            return True
        pendientes = [participante for participante in self.participantes if participante.pendiente()]
        if pendientes:
            opcion = decidir([participante.nombre for participante in pendientes])
            if opcion == "guardar":
                for participante in pendientes:
                    if not participante.guardar():
                        return False
            elif opcion == "descartar":
                for participante in pendientes:
                    participante.descartar()
            else:
                return False
        if any(participante.pendiente() for participante in self.participantes):
            return False
        self.cerrar_recursos()
        self.finalizar()
        self.finalizado = True
        return True
