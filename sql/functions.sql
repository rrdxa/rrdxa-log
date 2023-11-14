create or replace function rrdxa.op_time(op_time_multirange tstzmultirange)
  returns interval
  language sql stable
  return
    (select sum(upper(r) - lower(r)) from unnest($1) u(r));
