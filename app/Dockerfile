# Built from the repository root: the image installs the locked dependencies, then copies only the app.
FROM python:3.13.13-slim

ENV PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1 UV_PROJECT_ENVIRONMENT=/venv PATH=/venv/bin:$PATH
RUN pip install --no-cache-dir uv==0.11.17

WORKDIR /srv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app/ ./
RUN useradd --uid 10001 agent
USER agent

CMD ["python", "main.py"]
