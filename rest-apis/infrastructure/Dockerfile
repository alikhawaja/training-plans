FROM python:3.13.9-slim-bookworm

WORKDIR /app
COPY rest-apis/examples/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --gid 10001 training \
    && useradd --uid 10001 --gid training --no-create-home training \
    && mkdir /data && chown training:training /data
COPY rest-apis/examples/api.py .
USER training
ENV TRAINING_DB=/data/orders.db
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
