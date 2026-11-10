FROM python:3.12-slim
WORKDIR /app
COPY requirements-lock.txt .
RUN pip install --no-cache-dir -r requirements-lock.txt && useradd --uid 10001 --create-home autumn
COPY . .
RUN mkdir -p /state && chown 10001:10001 /state
USER 10001:10001
ENV AUTUMN_STATE=/state PYTHONDONTWRITEBYTECODE=1 LANGSMITH_TRACING=false
ENTRYPOINT ["python", "-m", "autumn.cli"]
CMD ["ask", "How long is backup retention?"]
