FROM python:3.11

ARG ENV_FILE

USER root

ENV \
 ENV_FILE=$ENV_FILE \
 PYTHONUNBUFFERED=1 \
 POETRY_VERSION=1.5.1 \
 TZ="Europe/Moscow"

RUN date

WORKDIR /api

COPY poetry.lock pyproject.toml ./
RUN pip install --upgrade pip "poetry==$POETRY_VERSION"
RUN poetry config virtualenvs.create false --local \
    && poetry install --without dev

COPY api .

COPY docker_init.sh .
RUN chmod 755 /api/docker_init.sh
ENTRYPOINT ["/api/docker_init.sh"]

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "1200"]
