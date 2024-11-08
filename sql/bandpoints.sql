create materialized view rrdxa.bandpoints as
select * from (
    select extract(year from start) as year, rrcalls.rroperator as rrmember, log_v.*,
        row_number() over (partition by extract(year from start), rrcalls.rroperator, major_mode, band, country order by start)
    from log_v
    join rrcalls on log_v.operator = rrcalls.rrcall
) where row_number = 1;
