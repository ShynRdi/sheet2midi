FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir '.[api,pdf]'

EXPOSE 8000
CMD ["uvicorn", "sheet2midi.api:app", "--host", "0.0.0.0", "--port", "8000"]
