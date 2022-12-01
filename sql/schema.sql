create schema if not exists rrdxa;
alter database rrdxa set search_path = public, rrdxa;
alter database rrdxa set timezone = 'UTC';

grant usage on schema rrdxa to public;
grant select on all tables in schema rrdxa to public;
alter default privileges in schema rrdxa grant select on tables to public;
