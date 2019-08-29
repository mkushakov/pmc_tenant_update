FROM python:3.7-alpine
WORKDIR /app
COPY PMC_TenantUpdate_API.py /app
RUN pip install --no-cache-dir --trusted-host pypi.python.org requests
ENTRYPOINT ["python", "/app/PMC_TenantUpdate_API.py"]