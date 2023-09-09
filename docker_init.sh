#!/bin/sh
alembic upgrade head
rm -rf alembic alembic.ini

exec "$@"