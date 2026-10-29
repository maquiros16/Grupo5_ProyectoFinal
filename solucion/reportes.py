"""RF-16. Consulta de reservaciones y exportación CSV, sin interfaz gráfica."""
import csv

from .contratos import Persistencia
from .validaciones import validar_rango_fechas


# Columnas del reporte en pantalla.
ENCABEZADOS = (
    "Estudiante", "Sala", "Fecha", "Horario", "Cantidad de personas", "Estado",
)

# Columnas del archivo CSV: incluye el carné y el horario con inicio y fin (BUG-05).
ENCABEZADOS_CSV = (
    "Carné", "Estudiante", "Sala", "Fecha", "Horario", "Cantidad de personas", "Estado",
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


# Da formato a una fila del reporte para la tabla de la pantalla.
def fila_pantalla(fila):
    return (fila.estudiante, fila.sala, fila.fecha, f"{fila.hora_inicio} ({fila.duracion} h)",
            fila.cantidad_personas, fila.estado)


# Da formato a una fila del reporte para el archivo CSV.
def fila_csv(fila):
    return (fila.carne, fila.estudiante, fila.sala, fila.fecha,
            f"{fila.hora_inicio}-{fila.hora_fin}", fila.cantidad_personas, fila.estado)


# Escribe el reporte ya consultado en un CSV con encabezados UTF-8.
def exportar_csv(filas, ruta):
    with open(ruta, "w", encoding="utf-8", newline="") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(ENCABEZADOS_CSV)
        escritor.writerows(fila_csv(fila) for fila in filas)
