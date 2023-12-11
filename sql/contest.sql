create table rrdxa.event (
    event_id serial primary key,
    cabrillo_name text,
    event text not null unique,
    start timestamptz(0) not null,
    stop timestamptz(0) not null,
    author text,
    created timestamptz(0) not null default now(),
    vhf boolean not null default false
);

comment on column rrdxa.event.event is 'Unique name of this event, e.g. "WAG 2023"';
comment on column rrdxa.event.cabrillo_name is 'Name of this event in Cabrillo CONTEST header, e.g. WAG';
