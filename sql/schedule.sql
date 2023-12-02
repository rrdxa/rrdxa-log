create table rrdxa.schedule (
    cabrillo_name text primary key,
    prefix text not null,
    dateformat text not null default 'YYYY',
    day int,
    month int,
    week int,
    dow int,
    start time not null,
    days int not null default 0,
    stop time not null
);

insert into schedule values ('ARRL-10M', 'ARRL-10M', 'YYYY', null, 12, 2, 6, '00:00', 1, '24:00');
insert into schedule values ('ARRL-160M', 'ARRL-160M', 'YYYY', null, 12, 1, 5, '22:00', 2, '16:00'); -- first Friday in December
insert into schedule values ('DARC-WAEDC-CW', 'WAEDC-CW', 'YYYY', null, 8, 2, 6, '00:00', 1, '24:00');
insert into schedule values ('DARC-WAEDC-RTTY', 'WAEDC-RTTY', 'YYYY', null, 11, 2, 6, '00:00', 1, '24:00');
insert into schedule values ('DARC-WAEDC-SSB', 'WAEDC-SSB', 'YYYY', null, 9, 2, 6, '00:00', 1, '24:00');
insert into schedule values ('DARC-XMAS', 'DARC-XMAS', 'YYYY', 26, 12, null, null, '8:30', 0, '11:00'); -- Dec 26th
insert into schedule values ('FT-ROUNDUP', 'FT-ROUNDUP', 'YYYY', null, 12, 1, 6, '18:00', 1, '24:00');
insert into schedule values ('MWC', 'MWC', 'YYMMDD', null, null, null, 1, '16:30', 0, '17:30'); -- every Monday
insert into schedule values ('OM-OK-DX', 'OM-OK-DX', 'YYYY', null, 11, 2, 6, '12:00', 1, '12:00');
insert into schedule values ('PRO-CW', 'PRO-CW', 'YYYY', null, 12, 1, 6, '12:00', 1, '12:00');
insert into schedule values ('WAG', 'WAG', 'YYYY', null, 10, 3, 6, '15:00', 1, '15:00');

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

    --raise notice 'day %, month %, week %, dow %', d_day, d_month, d_week, d_dow;

    for s in select * from schedule where
        (day is null or day = d_day) and
        (month is null or month = d_month) and
        (week is null or week = d_week) and
        (dow is null or dow = d_dow) loop

        insert into event (event, cabrillo_name, start, stop)
            values (s.prefix || ' ' || to_char(date, s.dateformat), s.cabrillo_name, date + s.start, date + s.days + s.stop)
            on conflict do nothing;
    end loop;

end;
$$;
