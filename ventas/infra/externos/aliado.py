"""Consumo del servicio que expone el EQUIPO ALIADO (Adapter).

El contrato del aliado no lo controlamos, asi que el adaptador normaliza
cualquier JSON razonable a `InfoAliadoDTO`:
  - una lista de objetos                      -> esos son los elementos
  - un objeto con alguna lista de objetos     -> se usa la primera lista
  - un objeto plano                           -> un unico elemento
De cada elemento se muestran solo campos simples (texto/numero/booleano).

Se configura con las variables de entorno ALIADO_API_URL y ALIADO_NOMBRE.
"""
from django.core.cache import cache
from django.utils.translation import gettext as _

from ventas.domain.dtos import InfoAliadoDTO
from ventas.domain.excepciones import ServicioNoDisponibleError
from ventas.domain.puertos import ServicioAliadoPort
from ventas.infra.http import ClienteHttp

MAX_ELEMENTOS = 12
MAX_CAMPOS = 6


def _plano(elemento: dict) -> dict:
    simples = {k: v for k, v in elemento.items() if isinstance(v, (str, int, float, bool)) and v is not None}
    return dict(list(simples.items())[:MAX_CAMPOS])


def normalizar(datos) -> list[dict]:
    if isinstance(datos, list):
        filas = datos
    elif isinstance(datos, dict):
        listas = [v for v in datos.values() if isinstance(v, list) and v and isinstance(v[0], dict)]
        filas = listas[0] if listas else [datos]
    else:
        filas = []
    return [_plano(f) for f in filas if isinstance(f, dict)][:MAX_ELEMENTOS]


class AliadoHttpAdapter(ServicioAliadoPort):
    SEGUNDOS_CACHE = 120

    def __init__(self, nombre: str, url: str):
        self.nombre = nombre
        self.url = url

    def consultar(self):
        if not self.url:
            return InfoAliadoDTO(nombre=self.nombre, disponible=False,
                                 mensaje=_("Aún no se ha configurado la URL del servicio aliado (ALIADO_API_URL)."))
        clave = f"aliado:{self.url}"
        en_cache = cache.get(clave)
        if en_cache:
            return en_cache
        try:
            r = ClienteHttp("servicio-aliado", self.url).get("")
        except ServicioNoDisponibleError:
            return InfoAliadoDTO(nombre=self.nombre, disponible=False, url=self.url,
                                 mensaje=_("El servicio del equipo aliado no responde en este momento."))
        if r.status != 200:
            return InfoAliadoDTO(nombre=self.nombre, disponible=False, url=self.url,
                                 mensaje=_("El servicio del equipo aliado respondió con un error."))
        info = InfoAliadoDTO(nombre=self.nombre, disponible=True, url=self.url, elementos=normalizar(r.datos))
        cache.set(clave, info, self.SEGUNDOS_CACHE)
        return info
