# Two images from one file:
#   docker build --target api -t citeverify-api .   -> REST API on :8000 (docs at /docs)
#   docker build --target app -t citeverify-app .   -> Streamlit app on :8501
# or simply: docker compose up

FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

FROM base AS api
COPY requirements-api.txt .
RUN pip install -r requirements-api.txt
COPY citeverify ./citeverify
USER nobody
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"
CMD ["uvicorn", "citeverify.api:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
USER nobody
ENV HOME=/tmp
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health')"
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
