create schema rrdxa;

create table rrdxa.upload (
    id serial primary key,
    uploader text not null,
    ts timestamptz not null default now(),
    filename text,
    station_callsign text,
    operator text,
    contest text,
    qsos integer,
    error text,
    adif text
);

create table rrdxa.log (
    start timestamptz not null,
    station_callsign text not null,
    operator text,
    call text not null,
    cty text,
    band band not null,
    freq numeric,
    mode text not null,
    rsttx text,
    rstrx text,
    gridsquare varchar(4),
    contest text,
    upload integer not null references rrdxa.upload (id) on delete cascade,
    adif jsonb,
    primary key (station_callsign, call, start)
) partition by range (start);

create index on log (call);

create extension pg_partman with schema public;

select public.create_parent('rrdxa.log', 'start', 'native', 'yearly',
    p_premake := 1, p_start_partition := '2000-01-01');

grant usage on schema rrdxa to public;
grant select on all tables in schema rrdxa to public;
alter default privileges in schema rrdxa grant select on tables to public;
