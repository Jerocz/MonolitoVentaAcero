"""Adaptadores HTTP hacia los microservicios Flask (implementan los puertos).

Cada adaptador traduce el contrato JSON de su microservicio a los DTOs del
dominio y los codigos HTTP a excepciones de dominio.
"""
from ventas.infra.microservicios.catalogo import CatalogoHttpAdapter
from ventas.infra.microservicios.fabricacion import FabricacionHttpAdapter
from ventas.infra.microservicios.pagos import PagosHttpAdapter

__all__ = ["CatalogoHttpAdapter", "FabricacionHttpAdapter", "PagosHttpAdapter"]
