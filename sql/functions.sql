create or replace function rrdxa.op_time(op_time_multirange tstzmultirange)
  returns interval
  language sql stable
  return
    (select sum(upper(r) - lower(r)) from unnest($1) u(r));

create or replace function rrdxa.month_str(start timestamptz)
  returns text
  stable parallel safe strict
  return
    to_char(start, 'FMMonth YYYY');

create or replace function rrdxa.start_str(start timestamptz)
  returns text
  stable parallel safe strict
  return
    to_char(start, 'DD.MM.YYYY HH24:MI');

create or replace function rrdxa.stop_str(stop timestamptz)
  returns text
  stable parallel safe strict
  return
    case when stop::time = '00:00' then to_char(stop - '1 day'::interval, 'DD.MM.YYYY 24:00')
    else to_char(stop, 'DD.MM.YYYY HH24:MI')
    end;
