-- cf. https://wiki.postgresql.org/wiki/Round_time

create or replace function rrdxa.qso_time_interval(start timestamptz, round_interval interval)
  returns tstzrange
  language sql stable
  return tstzrange(to_timestamp(extract(epoch from $1)::integer / extract(epoch from $2)::integer       * extract(epoch from $2)::integer),
                 to_timestamp(((extract(epoch from $1)::integer / extract(epoch from $2)::integer) + 1) * extract(epoch from $2)::integer));

create or replace function rrdxa.op_time(op_time_multirange tstzmultirange)
  returns interval
  language sql stable
  return
    (select sum(upper(r) - lower(r)) from unnest($1) u(r);
