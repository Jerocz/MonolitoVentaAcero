# Imagen del monolito Django (web) - tambien la usan el worker y el beat de Celery.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_STATIC_ROOT=/srv/static \
    DJANGO_MEDIA_ROOT=/srv/media

WORKDIR /srv/app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN useradd --create-home --uid 10001 django \
 && mkdir -p /srv/static /srv/media \
 && chown -R django /srv/app /srv/static /srv/media
USER django

EXPOSE 8000
CMD ["gunicorn", "monolito_venta_acero.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
