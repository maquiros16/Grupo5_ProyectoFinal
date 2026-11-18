# Sistema de reservación de salas de estudio

Aplicación de escritorio en Python para administrar estudiantes, salas y reservaciones de salas de estudio. Utiliza SQLite para conservar la información e incluye validaciones, consulta de disponibilidad, reportes e historial de auditoría.

## Información académica

- Curso: TI3603 Calidad en Sistemas de Información.
- Profesor: Néstor Morales Rodríguez.
- Institución: Tecnológico de Costa Rica.
- Semestre: Segundo semestre de 2026.
- Grupo: 5.

## Integrantes

- Emilio Alfaro Alfaro — 2024201356.
- Allan Andrey Jiménez Badilla — 2024080466.
- Melanie Parra Valverde — 2024239734.
- Marian Agüero Quirós — 2023176889.

## Requisitos de ejecución

- Python 3.10 o superior.
- Tkinter y Tcl/Tk disponibles.
- Una sesión gráfica para utilizar la aplicación y ejecutar las pruebas que crean ventanas.

La aplicación utiliza módulos de la biblioteca estándar de Python, como `sqlite3`, `tkinter`, `csv` y `unittest`. No requiere paquetes externos de pip.

El archivo `requirements.txt` documenta estos requisitos. Tkinter y SQLite no deben instalarse mediante pip. En Linux, Tkinter puede requerir la instalación de un paquete del sistema operativo, como `python3-tk` en Debian o Ubuntu.

## Estructura del repositorio

- `documentacion/`: documentación del proyecto.
- `solucion/`: código fuente de la aplicación.
- `pruebas/`: suite de pruebas automatizadas.
- `evidencias/`: capturas, exportaciones y registros de pruebas.
- `requirements.txt`: requisitos de ejecución y dependencias.
- `README.md`: instrucciones de preparación, ejecución, restauración y pruebas.

La carpeta `datos/` se genera automáticamente al iniciar la aplicación y contiene la base de datos SQLite. Esta carpeta no se incluye en el repositorio.

## Funcionalidades

- Registro, consulta y modificación de estudiantes.
- Activación e inactivación de estudiantes.
- Registro, consulta y modificación de salas.
- Cambio de estado de las salas.
- Creación, consulta, modificación y cancelación de reservaciones.
- Consulta de reservaciones por estudiante.
- Consulta de disponibilidad por sala, fecha y horario.
- Creación de series de reservaciones semanales.
- Cancelación individual o de ocurrencias futuras de una serie.
- Panel con reservaciones del día, próximas reservaciones y ocupación por sala.
- Filtros por fecha, sala y estado.
- Generación y exportación de reportes en CSV con codificación UTF-8.
- Consulta del historial de acciones.
- Persistencia local mediante SQLite.

## Preparación y ejecución

1. Descargar el repositorio mediante **Code → Download ZIP**.
2. Extraer el archivo ZIP.
3. Abrir una terminal en la carpeta que contiene `README.md`, `solucion/` y `pruebas/`.
4. Comprobar la versión de Python:

   ```bash
   python --version
   ```

5. Comprobar que Tkinter está disponible:

   ```bash
   python -m tkinter
   ```

   Debe abrirse una ventana de prueba. Cerrarla antes de continuar.

6. Iniciar la aplicación:

   ```bash
   python -m solucion.main
   ```

En Windows, si el comando `python` no está disponible, utilizar:

```powershell
py --version
py -m tkinter
py -m solucion.main
```

En Linux o macOS, si el intérprete se identifica como `python3`, utilizar:

```bash
python3 --version
python3 -m tkinter
python3 -m solucion.main
```

No es necesario instalar paquetes externos mediante pip.

## Datos iniciales y persistencia

En la primera ejecución, la aplicación crea automáticamente la base de datos:

```text
datos/reservaciones.sqlite3
```

La base se inicializa con los siguientes estudiantes:

| Carné | Nombre | Correo | Estado |
|---|---|---|---|
| A001234567 | Andrea Solano | andrea@universidad.ac.cr | activo |
| B009876543 | Carlos Méndez | carlos@universidad.ac.cr | activo |
| C004567890 | Daniela Rojas | daniela@universidad.ac.cr | inactivo |

También se cargan las siguientes salas:

| Código | Nombre | Capacidad | Estado |
|---|---|---:|---|
| S01 | Sala Biblioteca 1 | 4 | disponible |
| S02 | Sala Biblioteca 2 | 6 | disponible |
| S03 | Laboratorio de estudio | 10 | disponible |
| S04 | Sala multimedia | 8 | fuera_de_servicio |
| S05 | Cubículo individual | 1 | disponible |

Las ejecuciones posteriores utilizan la base existente y conservan los cambios registrados.

Las reservaciones y el historial de auditoría comienzan vacíos. Los identificadores de reservación se generan automáticamente con el formato `R0001`, continúan después de reiniciar y no se reutilizan al cancelar una reservación.

### Utilizar una base alternativa

Para realizar una demostración con una base separada, ejecutar:

```bash
python -m solucion.main --db datos/demostracion.sqlite3
```

Esta opción permite trabajar sin modificar la base habitual. Si el archivo indicado no existe, se crea con los datos iniciales.

## Restaurar los datos iniciales

Este procedimiento devuelve la base seleccionada a sus datos iniciales. Los cambios registrados dejan de estar disponibles en esa base, por lo que se debe conservar un respaldo.

1. Cerrar la aplicación.
2. Copiar `datos/reservaciones.sqlite3` en una ubicación de respaldo.
3. Eliminar el archivo original `datos/reservaciones.sqlite3`.
4. Iniciar nuevamente la aplicación:

   ```bash
   python -m solucion.main
   ```

La aplicación crea una nueva base con los estudiantes y las salas iniciales, sin reservaciones ni registros de auditoría.

Si se utiliza una base alternativa mediante `--db`, aplicar el procedimiento sobre ese archivo y volver a ejecutar la aplicación con la misma ruta.

## Reservaciones semanales

Se pueden solicitar series de entre 2 y 8 ocurrencias separadas por siete días. La interfaz permite previsualizar las fechas y los conflictos antes de confirmar.

Cada ocurrencia cuenta como una reservación para el límite de tres reservaciones activas presentes o futuras por estudiante. Por tanto, aunque el formulario admite solicitar hasta ocho ocurrencias, la serie solo se guarda si respeta ese límite.

Si las ocurrencias solicitadas, sumadas a las reservaciones vigentes del estudiante, superan el máximo de tres, se rechaza la serie completa. También se rechaza si alguna ocurrencia incumple las reglas de horario, capacidad o disponibilidad. No se guarda una serie parcialmente.

Desde el historial se puede cancelar una reservación individual o cancelar la ocurrencia futura seleccionada y las siguientes de su serie.

## Pruebas automatizadas

La suite utiliza `unittest` e incluye pruebas unitarias, de integración y de regresión.

Desde la raíz del proyecto, ejecutar:

```bash
python -m unittest discover -s pruebas -v
```

En Windows también se puede utilizar:

```powershell
py -m unittest discover -s pruebas -v
```

En Linux o macOS, si corresponde:

```bash
python3 -m unittest discover -s pruebas -v
```

Las pruebas que crean ventanas requieren Tkinter y una sesión gráfica disponible. Ejecutarlas en un entorno sin pantalla puede producir errores de inicialización gráfica o casos omitidos.

Para guardar la salida de una ejecución:

```bash
python -m unittest discover -s pruebas -v > evidencias/resultados_pruebas_actuales.txt 2>&1
```

Al interpretar el resumen:

- `OK` indica que no se registraron fallos ni errores en las pruebas ejecutadas.
- `FAILED` indica que existen fallos o errores que deben revisarse.
- `skipped` identifica pruebas omitidas, que no deben contarse como aprobadas.

El registro histórico `evidencias/F6_resultados_verificacion.txt` documenta una ejecución de 156 pruebas con resultado `OK`. Ese resultado corresponde a la ejecución registrada y no sustituye la verificación de cambios posteriores.

Después de modificar el código, ejecutar nuevamente la suite y conservar el resultado junto con la fecha, el sistema operativo, la versión de Python y el commit evaluado.

## Evidencias

La carpeta `evidencias/` conserva capturas, archivos CSV y registros de ejecuciones de distintas fases del proyecto.

Las evidencias de defectos y sus correcciones se mantienen para documentar el proceso de detección, corrección y verificación. Los resultados históricos deben interpretarse según la versión y el ambiente en que se obtuvieron.

Los escenarios históricos contienen fechas fijas. Para repetirlos, seleccionar fechas y horas válidas respecto al momento de la nueva ejecución.

