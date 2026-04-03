FROM python:3.12-slim

WORKDIR /app

# Install only production dependencies
COPY pyproject.toml README.md ./
COPY postagent/ postagent/
RUN pip install --no-cache-dir .

# Run database migrations on startup, then start the server
COPY schema.sql .

EXPOSE 8000

CMD ["uvicorn", "postagent.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
