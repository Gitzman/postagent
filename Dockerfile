FROM python:3.12-slim

WORKDIR /app

# Install only production dependencies
COPY pyproject.toml README.md ./
COPY postagent/ postagent/
RUN pip install --no-cache-dir .

# Copy schema for reference
COPY schema.sql .

# Non-root user
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"

CMD ["uvicorn", "postagent.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
