"""RF-16. Consulta de reservaciones y exportación CSV, sin interfaz gráfica."""
import csv

from .contratos import Persistencia
from .validaciones import validar_rango_fechas


ENCABEZADOS = (
    "Estudiante", "Sala", "Fecha", "Horario", "Cantidad de personas", "Estado",
)


class ServicioReportes:
    # Recibe el acceso a las reservaciones ya registradas.
    def __init__(self, persistencia: Persistencia):
        self.persistencia = persistencia

    # Consulta las reservaciones del rango, sin escribir el archivo.
    def generar(self, fecha_inicial, fecha_final):
        inicio, fin = validar_rango_fechas(fecha_inicial, fecha_final)
        with self.persistencia.lectura() as sesion:
            return sesion.listar_reporte(inicio, fin)


# Escribe el reporte ya consultado en un CSV con encabezados UTF-8.
def exportar_csv(filas, ruta):
    with open(ruta, "w", encoding="utf-8", newline="") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(ENCABEZADOS)
        escritor.writerows(filas)
