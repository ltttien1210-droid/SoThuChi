FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 LEDGER_DB=/var/lib/ledger/ledger.sqlite3
WORKDIR /srv
COPY requirements.txt .
COPY wheels ./wheels
RUN pip install --no-cache-dir --no-index --find-links=wheels -r requirements.txt && useradd -r -u 10001 ledger && install -d -m 700 -o ledger /var/lib/ledger
COPY app ./app
COPY manage.py .
USER ledger
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000","--proxy-headers","--forwarded-allow-ips","172.29.90.2","--limit-concurrency","64"]
