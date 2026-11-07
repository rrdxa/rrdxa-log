create table rrdxa.schedule (
    cabrillo_name text not null,
    prefix text not null,
    dateformat text not null default 'YYYY',
    day int,
    month int,
    week int,
    dow int,
    start time not null,
    days int not null default 0,
    stop time not null,
    vhf boolean not null default false,
    comment text
);

comment on column rrdxa.schedule.week is 'week number in month, negative numbers for "at least this many days before the end of the month"';

create or replace function rrdxa.last_week_in_month(date date, "offset" int)
    returns boolean
    return date between (date_trunc('month', date) + '1 month'::interval)::date - 6 + "offset"
                    and (date_trunc('month', date) + '1 month'::interval)::date + "offset";

comment on function rrdxa.last_week_in_month is 'date is in the last week of month (offset -1), or N days before that (offset <= -2)';

create or replace function rrdxa.schedule_events(date date default current_date)
    returns void
    language plpgsql
as $$
declare
    d_day int := extract(day from date);
    d_month int := extract(month from date);
    d_week int := ceil(d_day / 7.0); -- week number in month
    d_dow int := extract(dow from date);
    s record;
begin

    for s in select * from schedule where
        (day is null or day = d_day) and
        (month is null or month = d_month) and
        (week is null or week = d_week or (week < 0 and rrdxa.last_week_in_month(date, week))) and
        (dow is null or dow = d_dow) loop

        insert into event (event, cabrillo_name, start, stop, vhf)
            values (s.prefix || ' ' || to_char(date, s.dateformat), s.cabrillo_name, date + s.start, date + s.days + s.stop, s.vhf)
            on conflict do nothing;
    end loop;

end;
$$;
