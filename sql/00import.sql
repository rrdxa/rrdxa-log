begin;
\ir schema.sql
\ir functions.sql
\ir band.sql
\ir dxcc.sql
\ir mode.sql
\ir contest.sql
\ir log.sql
\ir schedule.sql
\copy rrdxa.schedule from data/contest-schedule.data (format csv, header)
\ir ../dxchallenge/bandpoints.sql
commit;

\ir wp_fdw.sql
