create table rrdxa.event (
    event_id serial primary key,
    contest_id integer, -- references rrdxa.contest(id),
    event text not null unique,
    period tstzrange not null,
    cabrillo_name text
);

comment on column rrdxa.event.event is 'Unique name of this event, e.g. "WAG 2023"';
comment on column rrdxa.event.period is 'Start and end time of this event';
comment on column rrdxa.event.cabrillo_name is 'Name of this event in Cabrillo CONTEST header';
