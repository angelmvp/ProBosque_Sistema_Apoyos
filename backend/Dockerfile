FROM python:3.13-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
COPY backend/requirements-dev.txt backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY backend/ ./
COPY docs/formatos /docs/formatos
ENV DIRECTORIO_FORMATOS=/docs/formatos DIRECTORIO_ARCHIVOS=/datos/archivos
RUN chmod +x /app/entrada.sh
EXPOSE 8000
CMD ["/app/entrada.sh"]
