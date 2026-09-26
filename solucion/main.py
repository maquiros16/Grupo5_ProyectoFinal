import argparse
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

from .aplicacion import Aplicacion
from .contratos import ErrorPersistencia
from .persistencia import PersistenciaSQLite


# Configura la persistencia e inicia el ciclo de la interfaz gráfica.
def main():
    argumentos = argparse.ArgumentParser(description="Sistema de reservación de salas")
    argumentos.add_argument(
        "--db", type=Path,
        default=Path(__file__).resolve().parents[1] / "datos" / "reservaciones.sqlite3",
    )
    opciones = argumentos.parse_args()
    try:
        persistencia = PersistenciaSQLite(opciones.db)
    except ErrorPersistencia as error:
        ventana = tk.Tk()
        ventana.withdraw()
        messagebox.showerror("No se pudo iniciar", str(error), parent=ventana)
        ventana.destroy()
        return 1
    try:
        aplicacion = Aplicacion(persistencia)
        aplicacion.mainloop()
    finally:
        persistencia.cerrar()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
