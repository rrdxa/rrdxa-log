create table rrdxa.event (
    event_id serial primary key,
    contest_id integer, -- references rrdxa.contest(id),
    event text not null unique,
    period tstzrange not null
);
