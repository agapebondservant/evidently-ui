FROM python:3.10-slim

WORKDIR ./workspace
COPY requirements.txt /tmp
RUN pip install -r /tmp/requirements.txt && \
    mkdir -p ./workspace

ENTRYPOINT evidently ui
CMD --workspace ./workspace --port 8080 –-demo-project --demo-project