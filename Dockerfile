FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY pyproject.toml README.md ./
COPY src ./src
COPY examples ./examples
# anaplan-grammar (pure Python) from its public repository; then this package with the web extras
RUN pip install --no-cache-dir "https://github.com/klameer/anaplan-grammar/archive/refs/heads/main.zip" \
 && pip install --no-cache-dir ".[web]"
EXPOSE 8000
CMD ["sh", "-c", "uvicorn anaplan_estate.web:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
