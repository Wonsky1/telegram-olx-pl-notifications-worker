FROM python:3.11-slim-buster

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ARG GROQ_MODEL_NAME
ARG GROQ_API_KEY
ARG TOPN_DB_BASE_URL

ENV GROQ_MODEL_NAME=${GROQ_MODEL_NAME}
ENV GROQ_API_KEY=${GROQ_API_KEY}
ENV TOPN_DB_BASE_URL=${TOPN_DB_BASE_URL}

CMD ["python", "main.py"]
