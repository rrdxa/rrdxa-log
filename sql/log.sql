create table rrdxa.upload (
    id serial primary key,
    uploader text not null,
    ts timestamptz(0) not null default now(),
    start timestamptz(0),
    stop timestamptz(0),
    filename text,
    station_callsign text,
    operator text,
    contest text,
    qsos integer,
    error text,
    adif text
    -- cabrillo fields
    operators text,
    club text,
    category_operator text,
    category_assisted text,
    category_band text,
    category_mode text,
    category_overlay text,
    category_power text,
    category_station text,
    category_time text,
    category_transmitter text,
    location text,
    grid_locator text,
    soapbox text,
    claimed_score integer,
    computed_score integer,
    event_id integer references event(event_id)
);

create table rrdxa.log (
    start timestamptz(0) not null,
    station_callsign text not null,
    operator text,
    call text not null,
    dxcc smallint references rrdxa.dxcc (dxcc),
    band band not null,
    freq numeric,
    major_mode mode_t not null,
    mode text,
    submode text,
    rsttx text,
    extx text,
    rstrx text,
    exrx text,
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
