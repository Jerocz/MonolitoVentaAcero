"""Configuracion de Django separada por responsabilidad y por entorno.

    entorno.py               utilidades para leer variables de entorno
    base.py                  lo comun a todos los entornos (apps, middleware, BD...)
    internacionalizacion.py  idiomas, zona horaria y catalogos gettext
    tareas_asincronas.py     Celery (Message Broker), cache y correo
    integraciones.py         microservicios, resiliencia, API de terceros y aliado
    empresa.py               datos de contacto que muestran las plantillas

    desarrollo.py            entorno local   (DEBUG activo, SQLite por defecto)
    produccion.py            Docker / AWS    (DEBUG apagado, claves obligatorias)

El entorno se elige con DJANGO_SETTINGS_MODULE, por ejemplo
`monolito_venta_acero.settings.produccion`.
"""
