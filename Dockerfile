FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 APP_ENV=production \
    DATABASE_PATH=/data/travelinsight.db
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd -m app && mkdir -p /data && chown -R app /data /app
USER app
VOLUME /data
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request,os;urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8000')+'/api/health')" || exit 1
CMD ["sh", "-c", "python manage.py init-db && exec gunicorn wsgi:app --workers 2 --threads 4 --timeout 60 --bind 0.0.0.0:${PORT:-8000}"]
