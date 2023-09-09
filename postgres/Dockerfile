FROM postgres

WORKDIR /var/lib/postgresql

RUN mkdir /var/lib/PostgresConfig
COPY init.sql /docker-entrypoint-initdb.d/init.sql

CMD ["postgres", "-c",  "config_file=/var/lib/PostgresConfig/postgresql.conf"]
