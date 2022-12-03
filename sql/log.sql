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
    dxcc smallint references rrdxa.dxcc (dxcc),
    band band not null,
    freq numeric,
    major_mode text not null,
    mode text not null,
    rsttx text,
    rstrx text,
    gridsquare varchar(4),
    contest text,
    upload integer not null references rrdxa.upload (id) on delete cascade,
    adif jsonb,
    primary key (station_callsign, call, band, major_mode, start)
);

grant select, insert, update, delete on rrdxa.upload, rrdxa.log to "www-data";
grant usage on rrdxa.upload_id_seq to "www-data";

create index on rrdxa.log (start);
create index on rrdxa.log (operator);
create index on rrdxa.log (call);
create index on rrdxa.log (dxcc);
create index on rrdxa.log (gridsquare);
create index on rrdxa.log (contest);
create index on rrdxa.log (upload);
