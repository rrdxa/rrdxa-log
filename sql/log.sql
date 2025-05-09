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
    adif text,
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
    event_id integer references event(event_id),
    exchange text,
    constraint station_callsign_event_unique unique (station_callsign, event_id)
);

create or replace view rrdxa.upload_operators as
    select id,
        station_callsign,
        op operator,
        qsos,
        array_length(ops, 1) n_operators,
        event_id
    from rrdxa.upload,
        regexp_split_to_array(coalesce(nullif(operators, ''), nullif(operator, ''), rrdxa.basecall(station_callsign)), '[\s,]+') as ops,
        unnest(ops) as u(op)
    where qsos > 0;

create table rrdxa.log (
    start timestamptz(0) not null,
    station_callsign text not null,
    operator text,
    call text not null,
    dxcc smallint references rrdxa.dxcc (dxcc),
    band rrdxa.band not null,
    freq numeric,
    major_mode rrdxa.mode_t not null,
    mode text,
    submode text,
    rsttx text,
    extx text,
    rstrx text,
    exrx text,
    gridsquare varchar(6),
    contest text,
    upload integer not null references rrdxa.upload (id) on delete cascade,
    adif jsonb,
    primary key (station_callsign, call, band, major_mode, start)
);

create or replace view rrdxa.log_v as
    select
        start, to_char(start, 'DD.MM.YYYY') as start_str,
        station_callsign, coalesce(operator, station_callsign) as operator,
        call, rrdxa.basecall(call), rrcalls.rroperator,
        dxcc.country,
        band, freq,
        major_mode, mode, submode,
        rsttx, extx,
        rstrx, exrx,
        gridsquare,
        contest,
        upload
    from log
    left join dxcc on log.dxcc = dxcc.dxcc
    left join rrcalls on basecall(log.call) = rrcalls.rrcall;

grant select, insert, update, delete on rrdxa.upload, rrdxa.log to "www-data";
grant usage on rrdxa.upload_id_seq to "www-data";

create index on rrdxa.log (start);
create index log_operator_start_idx on rrdxa.log (coalesce(operator, station_callsign), start);
create index on rrdxa.log (call);
create index on rrdxa.log (basecall(call));
create index on rrdxa.log (dxcc);
create index on rrdxa.log (gridsquare);
create index on rrdxa.log (contest);
create index on rrdxa.log (upload);
