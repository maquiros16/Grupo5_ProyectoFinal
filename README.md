# Sistema de reservación de salas de estudio

Aplicación de escritorio en Python para administrar estudiantes, salas y reservaciones de salas de estudio. Utiliza SQLite para conservar la información e incluye validaciones, consulta de disponibilidad, reportes e historial de auditoría.

## Información académica

- Curso: TI3603 Calidad en Sistemas de Información
- Profesor: Néstor Morales
- Institución: Tecnológico de Costa Rica
- Semestre: Segundo semestre de 2026
- Grupo: 5

## Integrantes

- Emilio Alfaro Alfaro - 2024201356
- Allan Andrey Jiménez Badilla - 2024080466
- Melanie Parra Valverde - 2024239734
- Marian Agüero Quirós - 2023176889

## Tecnologías

- Python 3.10 o superior
- SQLite mediante el módulo `sqlite3`
- Interfaz gráfica de escritorio con Tkinter
- CSV con codificación UTF-8
- Pruebas automatizadas con `unittest`

## Estructura del repositorio

- `documentacion/`: informe final, manual de usuario y matriz de trazabilidad.
- `solucion/`: código fuente y datos de la aplicación.
- `pruebas/`: pruebas automatizadas, datos de prueba y resultados.
- `evidencias/`: capturas y registros de las pruebas realizadas.

## Reservaciones semanales

Se pueden crear series de 2 a 8 reservaciones separadas por siete días. La interfaz permite previsualizar las fechas y los conflictos antes de confirmar. Si alguna semana incumple las reglas, no se guarda ninguna reservación de la serie.

Cada ocurrencia de una serie cuenta como una reservación para el límite de tres reservaciones activas presentes o futuras por estudiante. Si las ocurrencias solicitadas, sumadas a las reservaciones vigentes del estudiante, superan ese límite, se rechaza la serie completa sin guardar ninguna ocurrencia.  Desde el historial se puede cancelar una reservación individual o cancelar la semana seleccionada y las siguientes ocurrencias futuras de su serie.

## Instalación y ejecución

Se requiere Python 3.10 o superior con Tkinter disponible. La aplicación utiliza módulos de la biblioteca estándar de Python y no requiere paquetes externos de pip.

1. Descargar el repositorio mediante Code → Download ZIP.
2. Extraer el archivo ZIP.
3. Abrir una terminal en la carpeta que contiene README.md, solucion y pruebas.
4. Ejecutar:

```bash
python -m solucion.main
```

En Windows, si el comando anterior no funciona, utilizar:

```powershell
py -m solucion.main
```

En la primera ejecución se crea automáticamente la base de datos `datos/reservaciones.sqlite3`, con los estudiantes y las salas iniciales. Las siguientes ejecuciones conservan los datos registrados.

## Restaurar los datos iniciales

Este procedimiento elimina los cambios registrados y devuelve la aplicación a sus datos iniciales.

1. Cerrar la aplicación.
2. Guardar una copia de respaldo de `datos/reservaciones.sqlite3`.
3. Eliminar el archivo original `datos/reservaciones.sqlite3`.
4. Ejecutar nuevamente la aplicación. La base de datos se creará con los datos iniciales.
   
## Pruebas

Desde la raíz del proyecto, ejecutar:

```powershell
py -3.13 -m unittest discover -s pruebas -v
```

La última ejecución completó 86 pruebas correctamente.
