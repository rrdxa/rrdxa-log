create table rrdxa.dxcc (
    dxcc smallint primary key,
    country text not null,
    deleted boolean not null
);

\copy rrdxa.dxcc (dxcc, country, deleted) from 'sql/dxcc.data'
