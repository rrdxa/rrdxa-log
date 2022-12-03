create type rrdxa.band AS enum (
    '2190m', '630m', '560m',
    '160m', '80m', '60m', '40m', '30m', '20m', '17m', '15m', '12m', '10m',
    '8m', '6m', '4m', '5m', '2m', '1.25m',
    '70cm', '33cm', '23cm', '13cm', '9cm', '6cm', '3cm', '1.25cm',
    '6mm', '4mm', '2.5mm', '2mm', '1mm',
    'unknown'
);

create or replace function rrdxa.band(freq numeric) returns band
language sql
return case
    when freq between 0.1357 and 0.1378     then '2190m'::rrdxa.band
    when freq between 0.472 and 0.479       then '630m'
    when freq between 0.501 and 0.504       then '560m'
    when freq between 1.8 and 2.0           then '160m'
    when freq between 3.5 and 4.0           then '80m'
    when freq between 5.06 and 5.45         then '60m'
    when freq between 7.0 and 7.3           then '40m'
    when freq = 10.0                        then '30m'
    when freq between 10.1 and 10.15        then '30m'
    when freq between 14.0 and 14.35        then '20m'
    when freq = 18.0                        then '17m'
    when freq between 18.068 and 18.168     then '17m'
    when freq between 21.0 and 21.45        then '15m'
    when freq = 24.0                        then '12m'
    when freq between 24.89 and 24.99       then '12m'
    when freq between 28.0 and 29.7         then '10m'
    when freq between 40.0 and 45.0         then '8m'
    when freq between 50.0 and 54.0         then '6m'
    when freq between 54.000001 and 69.9    then '5m'
    when freq between 70.0 and 71.0         then '4m'
    when freq between 144.0 and 148.0       then '2m'
    when freq between 222.0 and 225.0       then '1.25m'
    when freq between 420.0 and 450.0       then '70cm'
    when freq between 902.0 and 928.0       then '33cm'
    when freq between 1240.0 and 1300.0     then '23cm'
    when freq between 2300.0 and 2450.0     then '13cm'
    when freq between 3300.0 and 3500.0     then '9cm'
    when freq between 5650.0 and 5925.0     then '6cm'
    when freq between 10000.0 and 10500.0   then '3cm'
    when freq between 24000.0 and 24250.0   then '1.25cm'
    when freq between 47000.0 and 47200.0   then '6mm'
    when freq between 75500.0 and 81000.0   then '4mm'
    when freq between 119980.0 and 120020.0 then '2.5mm'
    when freq between 142000.0 and 149000.0 then '2mm'
    when freq between 241000.0 and 250000.0 then '1mm'
    else 'unknown'
end;

create cast (numeric as rrdxa.band) with function rrdxa.band as assignment;
