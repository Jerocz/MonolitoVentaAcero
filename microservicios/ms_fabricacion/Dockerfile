FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv/app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN useradd --create-home --uid 10001 servicio && chown -R servicio /srv/app
USER servicio

EXPOSE 5000
HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5000/api/fabricacion/health', timeout=2).status == 200 else 1)"

CMD ["sh", "-c", "python -m app.init_db && gunicorn wsgi:app --bind 0.0.0.0:5000 --workers 2 --access-logfile -"]
