FROM python:3.11-slim
WORKDIR /app

COPY requirements.in .

RUN pip install --upgrade pip \
    && pip install --no-cache-dir pip-tools \
    && pip-compile requirements.in --output-file=requirements.txt \
    && pip install --no-cache-dir -r requirements.txt

COPY . .
ENV PYTHONPATH =/app

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "80"]