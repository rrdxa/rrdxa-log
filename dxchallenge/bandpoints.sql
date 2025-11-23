create materialized view rrdxa.bandpoints as
select
year,
    rrmember,
    start,
    station_callsign,
    operator,
    major_mode,
    mode,
    submode,
    band,
    call,
    dxcc
from (
    select extract(year from start) as year, rrcalls.rroperator as rrmember, start::date, station_callsign, operator, major_mode, mode, submode, band, call, dxcc,
        row_number() over (partition by extract(year from start), rrcalls.rroperator, major_mode, band, dxcc order by start)
    from log
    join rrcalls on coalesce(operator, station_callsign) = rrcalls.rrcall
    where
        major_mode <> 'unknown' and
        band <> 'unknown' and
        dxcc between 1 and 950
) where row_number = 1
order by year, major_mode, rrmember;

create index on rrdxa.bandpoints(year);
