create schema rrdxa;

create table rrdxa.person (
    person text primary key,
    last_seen timestamptz
);

create table rrdxa.call (
    call text primary key
);

create table rrdxa.person_call (
    person text not null references rrdxa.person,
    call text not null references rrdxa.call,
    primary key (person, call)
);

create table rrdxa.upload (
    id serial primary key,
    person text not null references rrdxa.person,
    ts timestamptz not null default now(),
    call text,
    operator text,
    contest text,
    qsos integer,
    error text,
    adif text
);

create table rrdxa.log (
    start timestamptz not null,
    station_callsign text not null references rrdxa.call (call),
    operator text references rrdxa.call (call),
    call text not null,
    cty text,
    band band not null,
    freq numeric,
    mode text not null,
    rsttx text,
    rstrx text,
    contest text,
    upload integer not null references rrdxa.upload (id) on delete cascade,
    adif jsonb,
    primary key (station_callsign, call, start)
) partition by range (start);

create index on log (call);

create table rrdxa.log_2022
    partition of rrdxa.log
    for values from ('2022-01-01') to ('2023-01-01');

create table rrdxa.log_default
    partition of rrdxa.log
    default;
