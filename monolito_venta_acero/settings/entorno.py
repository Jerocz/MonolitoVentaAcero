"""Lectura de variables de entorno (12-factor)."""
import os


def env_texto(nombre: str, defecto: str = "") -> str:
    return os.getenv(nombre, defecto)


def env_bool(nombre: str, defecto: bool = False) -> bool:
    return os.getenv(nombre, str(defecto)).strip().lower() in ("1", "true", "si", "yes", "on")


def env_entero(nombre: str, defecto: int) -> int:
    return int(os.getenv(nombre, str(defecto)))


def env_decimal(nombre: str, defecto: float) -> float:
    return float(os.getenv(nombre, str(defecto)))


def env_lista(nombre: str, defecto: str = "") -> list[str]:
    return [v.strip() for v in os.getenv(nombre, defecto).split(",") if v.strip()]


def env_obligatoria(nombre: str) -> str:
    valor = os.getenv(nombre)
    if not valor:
        raise RuntimeError(f"Falta la variable de entorno obligatoria {nombre}.")
    return valor
