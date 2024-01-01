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
    vhf boolean not null default false
);

comment on column rrdxa.schedule.week is 'week number in month, negative numbers for "at least this many days before the end of the month"';

-- yearly contests
-- the big ones
insert into schedule values ('CQ-WW-160M',      'CQ-WW-160M',   'YYYY', null,  1,-3, 5, '22:00', 2, '22:00'); -- last full weekend including Friday
insert into schedule values ('CQ-WW-RTTY',      'CQ-WW-RTTY',   'YYYY', null,  9,-2, 6, '00:00', 1, '24:00');
insert into schedule values ('CQ-WW-SSB',       'CQ-WW-SSB',    'YYYY', null, 10,-2, 6, '00:00', 1, '24:00');
insert into schedule values ('CQ-WW-CW',        'CQ-WW-CW',     'YYYY', null, 11,-2, 6, '00:00', 1, '24:00');
insert into schedule values ('CQ-WPX-RTTY',     'CQ-WPX-RTTY',  'YYYY', null,  2, 2, 6, '00:00', 1, '24:00');
insert into schedule values ('CQ-WPX-SSB',      'CQ-WPX-SSB',   'YYYY', null,  3,-2, 6, '00:00', 1, '24:00');
insert into schedule values ('CQ-WPX-CW',       'CQ-WPX-CW',    'YYYY', null,  5,-2, 6, '00:00', 1, '24:00');

-- ARRL
insert into schedule values ('ARRL-RU-RTTY',    'ARRL-RU-RTTY', 'YYYY', null,  1, 1, 6, '18:00', 1, '24:00');
insert into schedule values ('ARRL-DX-CW',      'ARRL-DX-CW',   'YYYY', null,  2, 3, 6, '00:00', 1, '24:00');
insert into schedule values ('ARRL-DX-SSB',     'ARRL-DX-SSB',  'YYYY', null,  3, 1, 6, '00:00', 1, '24:00');
insert into schedule values ('ARRL-160M',       'ARRL-160M',    'YYYY', null, 12, 1, 5, '22:00', 2, '16:00'); -- first Friday in December
insert into schedule values ('ARRL-10M',        'ARRL-10M',     'YYYY', null, 12, 2, 6, '00:00', 1, '24:00');

-- DARC
insert into schedule values ('DARC-10M',        'DARC-10M',     'YYYY', null,  1, 2, 0, '09:00', 0, '11:00');
insert into schedule values ('DARC-WAEDC-CW',   'WAEDC-CW',     'YYYY', null,  8, 2, 6, '00:00', 1, '24:00');
insert into schedule values ('DARC-WAEDC-SSB',  'WAEDC-SSB',    'YYYY', null,  9, 2, 6, '00:00', 1, '24:00');
insert into schedule values ('DARC-AC',         'DARC-AC',      'YYYY', null, 10, 3, 6, '12:00', 0, '14:30');
insert into schedule values ('WAG',             'WAG',          'YYYY', null, 10, 3, 6, '15:00', 1, '15:00');
insert into schedule values ('DARC-WAEDC-RTTY', 'WAEDC-RTTY',   'YYYY', null, 11, 2, 6, '00:00', 1, '24:00');
insert into schedule values ('DARC-XMAS',       'DARC-XMAS',    'YYYY', 26,   12, null, null, '8:30', 0, '11:00'); -- Dec 26th

-- contests that come in pairs
insert into schedule values ('REF-CW',          'REF-CW',       'YYYY', null,  1,-2, 6, '06:00', 1, '18:00');
insert into schedule values ('REF-SSB',         'REF-SSB',      'YYYY', null,  2,-2, 6, '06:00', 1, '18:00');
insert into schedule values ('UBA-DX-SSB',      'UBA-DX-SSB',   'YYYY', null,  1,-2, 6, '13:00', 1, '13:00');
insert into schedule values ('UBA-DX-CW',       'UBA-DX-CW',    'YYYY', null,  2,-2, 6, '13:00', 1, '13:00');
insert into schedule values ('UKEIDX-CW',       'UKEIDX-CW',    'YYYY', null,  4,-2, 6, '12:00', 1, '12:00');
-- UKEIDX-SSB doesn't have a fixed schedule (https://www.ukeicc.com/dx-contest-rules.php)
--insert into schedule values ('UKEIDX-SSB',      'UKEIDX-SSB',   'YYYY', null,  9,-2, 6, '12:00', 1, '12:00');
insert into schedule values ('EA-MAJESTAD-CW', 'EA-MAJESTAD-CW','YYYY', null,  5, 3, 6, '12:00', 1, '12:00');
insert into schedule values ('EA-MAJESTAD-SSB','EA-MAJESTAD-SSB','YYYY',null,  6, 4, 6, '12:00', 1, '12:00');
insert into schedule values ('IARU-R1-FD-CW',  'IARU-R1-FD-CW', 'YYYY', null,  6, 1, 6, '15:00', 1, '15:00');
insert into schedule values ('IARU-R1-FD-SSB', 'IARU-R1-FD-SSB','YYYY', null,  9, 1, 6, '13:00', 1, '13:00');
insert into schedule values ('ALL-ASIAN-CW',    'ALL-ASIAN-CW', 'YYYY', null,  6, 3, 6, '00:00', 1, '24:00');
insert into schedule values ('ALL-ASIAN-SSB',   'ALL-ASIAN-SSB','YYYY', null,  9, 1, 6, '00:00', 1, '24:00');
insert into schedule values ('SAC-CW',          'SAC-CW',       'YYYY', null,  9, 3, 6, '12:00', 1, '12:00');
insert into schedule values ('SAC-SSB',         'SAC-SSB',      'YYYY', null, 10, 2, 6, '12:00', 1, '12:00');

-- Stew Perry
insert into schedule values ('STEW-PERRY',      'STEW-PERRY',   'YYYY-MM', null,  3, 2, 6, '15:00', 1, '15:00');
insert into schedule values ('STEW-PERRY',      'STEW-PERRY',   'YYYY-MM', null,  6, 3, 6, '15:00', 1, '15:00');
insert into schedule values ('STEW-PERRY',      'STEW-PERRY',   'YYYY-MM', null,  8, 3, 6, '15:00', 1, '15:00');
insert into schedule values ('STEW-PERRY',      'STEW-PERRY',   'YYYY-MM', null, 12,-2, 6, '15:00', 1, '15:00');

-- everything else
insert into schedule values ('AGCW-HNY',        'AGCW-HNY',     'YYYY', 1,     1, null, null, '09:00', 0, '12:00');
insert into schedule values ('HA-DX',           'HA-DX',        'YYYY', null,  1, 3, 6, '12:00', 1, '12:00');
insert into schedule values ('EU-DX',           'EU-DX',        'YYYY', null,  2, 1, 6, '12:00', 1, '12:00');
insert into schedule values ('WOMENS-DAY',      'WOMENS-DAY',   'YYYY', 8,     3, null, null, '18:00', 0, '21:00'); -- Mar 8th
insert into schedule values ('CQMM',            'CQMM',         'YYYY', null,  4, 3, 6, '09:00', 1, '24:00');
insert into schedule values ('HELVETIA',        'HELVETIA',     'YYYY', null,  4,-1, 6, '13:00', 1, '13:00');
insert into schedule values ('MMC',             'MMC',          'YYYY', null,  7, 1, 6, '14:00', 1, '14:00');
insert into schedule values ('IOTA',            'IOTA',         'YYYY', null,  7,-2, 6, '12:00', 1, '12:00');
insert into schedule values ('YO-DX',           'YO-DX',        'YYYY', null,  8,-2, 6, '12:00', 1, '12:00');
insert into schedule values ('MARCONI-VHF',     'MARCONI-VHF',  'YYYY', null, 11, 1, 6, '14:00', 1, '14:00');
insert into schedule values ('OM-OK-DX',        'OM-OK-DX',     'YYYY', null, 11, 2, 6, '12:00', 1, '12:00');
insert into schedule values ('LZ-DX',           'LZ-DX',        'YYYY', null, 11,-9, 6, '12:00', 1, '12:00'); -- last weekend before CQ-WW-CW
insert into schedule values ('PRO-CW',          'PRO-CW',       'YYYY', null, 12, 1, 6, '12:00', 1, '12:00');
insert into schedule values ('FT-ROUNDUP',      'FT-ROUNDUP',   'YYYY', null, 12, 1, 6, '18:00', 1, '24:00');
insert into schedule values ('OK-DX-RTTY',      'OK-DX-RTTY',   'YYYY', null, 12, 3, 6, '00:00', 0, '24:00');
insert into schedule values ('9A-DX',           '9A-DX',        'YYYY', null, 12, 3, 6, '14:00', 1, '24:00');

-- monthly contests
insert into schedule values ('FT8-ACTIVITY-2M',   'FT8-ACTIVITY 2M',   'YYYY-MM', null, null, 1, 3, '17:00', 0, '21:00', 't'); -- 1st Monday, VHF
insert into schedule values ('FT8-ACTIVITY-70CM', 'FT8-ACTIVITY 70CM', 'YYYY-MM', null, null, 2, 3, '17:00', 0, '21:00', 't'); -- 2nd Monday, VHF
insert into schedule values ('FT8-ACTIVITY-23CM', 'FT8-ACTIVITY 23CM', 'YYYY-MM', null, null, 3, 3, '17:00', 0, '21:00', 't'); -- 3rd Monday, VHF

-- weekly contests
insert into schedule values ('MWC', 'MWC', 'YYMMDD', null, null, null, 1, '16:30', 0, '17:30'); -- every Monday

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
