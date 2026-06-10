FROM python:3.11-slim

RUN useradd --create-home --uid 10001 sandbox
WORKDIR /app
COPY runner.py /app/runner.py
RUN chown -R sandbox:sandbox /app

USER sandbox
EXPOSE 8091
CMD ["python", "/app/runner.py"]
