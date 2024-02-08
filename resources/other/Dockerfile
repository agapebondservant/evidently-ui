FROM python:3.10-slim

COPY requirements.txt /tmp
COPY monitoring.py /tmp
RUN pip install -r /tmp/requirements.txt && mkdir -p ./workspace
COPY workspace/. /workspace/

ENTRYPOINT ["evidently ui"]
CMD ["--port", "8080", "--demo-projects", "all"]