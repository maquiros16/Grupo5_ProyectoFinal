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

Una serie con reservaciones activas presentes o futuras cuenta como una unidad para el límite de tres unidades por estudiante. Desde el historial se puede cancelar una reservación individual o cancelar la semana seleccionada y las siguientes de su serie.

## Pruebas

Desde la raíz del proyecto, ejecutar:

```powershell
py -3.13 -m unittest discover -s pruebas -v
```

La última ejecución completó 86 pruebas correctamente.