FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements-modelscope.txt requirements.txt ./
RUN pip install --no-cache-dir -r requirements-modelscope.txt
COPY webapp ./webapp
COPY fengshui-audit ./fengshui-audit
COPY modelscope_app.py ./
RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser
EXPOSE 7860
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "--workers", "1", "--threads", "4", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "modelscope_app:app"]
