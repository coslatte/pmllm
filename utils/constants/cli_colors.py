import typer

# Esquema restringido a 4 colores:
# ROJO   -> Errores / fallos
# VERDE  -> Éxitos / completado
# BLANCO -> Información neutra / pasos / notas
# NEGRO  -> Fondo (no se fuerza para texto para evitar bajo contraste)

ERROR = typer.colors.RED
SUCCESS = typer.colors.GREEN
INFO = typer.colors.WHITE
BACKGROUND = typer.colors.BLACK

COLOR = {
    "ERROR": ERROR,
    "SUCCESS": SUCCESS,
    "INFO": INFO,
    "BACKGROUND": BACKGROUND,
}
