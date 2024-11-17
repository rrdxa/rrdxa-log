create materialized view rrdxa.bandpoints as
select * from (
    select extract(year from start) as year, rrcalls.rroperator as rrmember, start::date, station_callsign, operator, major_mode, mode, submode, band, call, dxcc,
        row_number() over (partition by extract(year from start), rrcalls.rroperator, major_mode, band, dxcc order by start)
    from log
    join rrcalls on coalesce(operator, station_callsign) = rrcalls.rrcall
    where
        major_mode <> 'unknown' and
        band <> 'unknown' and
        dxcc between 1 and 950 and
        start < current_date
) where row_number = 1;

create table rrdxa.previous_bandpoints as
select * from rrdxa.bandpoints;

create index on rrdxa.previous_bandpoints (major_mode, dxcc, band);

create table rrdxa.bandpoints_history (
    date date,
    rrmember text,
    major_mode mode_t,
    band band,
    count int,
    dxccs smallint[],
    rank int,
    constraint bandpoints_history_key unique nulls distinct (date, rrmember, major_mode, band)
);

    select distinct start::date, major_mode, band, dxcc, count(*)
    from log
    where
        major_mode <> 'unknown' and
        band <> 'unknown' and
        dxcc between 1 and 950
    group by 1, 2, 3, 4
    order by 1, 2, 3, 4;
