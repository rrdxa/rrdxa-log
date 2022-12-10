create type rrdxa.mode as enum ('CW', 'PHONE', 'DIGI', 'unknown');

create or replace function rrdxa.major_mode(submode text)
    returns mode
    language sql
    return case
        when submode is null then 'unknown'
        when upper(submode) in ('CW', 'CW-R', 'A1A') then 'CW'::mode
        when upper(submode) in ('PHONE', 'PH',
            'SSB', 'LSB', 'USB', 'J3E',
            'FM', 'F3E', 'AM',
            'DIGITALVOICE', 'C4FM', 'DMR', 'DSTAR') then 'PHONE'
        else 'DIGI'
    end;
