create type rrdxa.continent as enum ('NA', 'SA', 'EU', 'AF', 'OC', 'AS', 'AN');

create table rrdxa.dxcc (
    dxcc smallint primary key,
    country text not null,
    deleted boolean not null,
    cont rrdxa.continent
);

\copy rrdxa.dxcc (dxcc, country, deleted) from 'sql/dxcc.data'
