# syntax=docker/dockerfile:1
# notes service: Python standard library only, so there is nothing to pip install.
FROM python:3.12-slim

# Unbuffered output so logs show up in `docker compose logs` straight away.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

WORKDIR /app
COPY *.py ./

# Run as an unprivileged user rather than root.
RUN useradd --system --uid 10001 app \
    && mkdir -p /data && chown app /data
USER app

EXPOSE 8000
VOLUME ["/data"]
HEALTHCHECK --interval=5s --timeout=3s --start-period=5s --retries=5 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.environ['PORT'], timeout=2)"

CMD ["python", "app.py"]
