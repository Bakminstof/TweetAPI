DO
$$
BEGIN
   IF NOT EXISTS (SELECT extname FROM pg_catalog.pg_extension WHERE extname = 'dblink')
   THEN
     CREATE EXTENSION dblink;
   END IF;

   IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'twt_db')
   THEN
      CREATE ROLE twt WITH LOGIN CREATEDB;
      ALTER USER twt WITH PASSWORD 'WBtTMEqtsQyMTTb+GtEd9BHUzaB5qWaDy8vYCLrE';

      PERFORM dblink_exec(
      'user=ADMIN password=aoisfBGq*^&#t*#&H)(gh)(@$#*T0H209GH*@g0[32hg-#q90221J980gh dbname=' || current_database(),
        'CREATE DATABASE twt_db'
      );

      GRANT ALL ON DATABASE twt_db TO twt;

      ALTER DATABASE twt_db OWNER TO twt;
   END IF;
END;
$$