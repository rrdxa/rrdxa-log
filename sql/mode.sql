create type rrdxa.mode as enum ('CW', 'PHONE', 'DIGI');

create or replace function rrdxa.major_mode(submode text)
    returns mode
    language sql
    return case
        when upper(submode) = 'CW' then 'CW'::mode
        when upper(submode) in ('PHONE', 'SSB', 'LSB', 'USB', 'FM', 'AM',
            'DIGITALVOICE', 'C4FM', 'DMR', 'DSTAR') then 'PHONE'
        else 'DIGI'
    end;
