create table rrdxa.event (
    event_id serial primary key,
    cabrillo_name text,
    event text not null unique,
    start timestamptz(0) not null,
    stop timestamptz(0) not null,
    author text,
    created timestamptz(0) not null default now(),
    vhf boolean not null default false,
    constraint event_name_includes_year check (event ~ to_char(start, 'YY')),
    constraint event_min_duration check (stop >= start + '30min'::interval),
    constraint event_max_duration check (stop <= start + '7d'::interval)
);

comment on column rrdxa.event.event is 'Unique name of this event, e.g. "WAG 2023"';
comment on column rrdxa.event.cabrillo_name is 'Name of this event in Cabrillo CONTEST header, e.g. WAG';
