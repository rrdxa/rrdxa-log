create type rrdxa.mode_t as enum ('CW', 'PHONE', 'DIGI', 'FT8', 'unknown');

create or replace function rrdxa.major_mode(mode text, submode text default null)
    returns rrdxa.mode_t
    language sql
    return case
        when mode is null then 'unknown'::rrdxa.mode_t
        when upper(mode) in ('CW', 'CW-R', 'A1A') then 'CW'
        when upper(mode) in ('PHONE', 'PH',
            'SSB', 'LSB', 'USB', 'J3E',
            'FM', 'F3E', 'AM',
            'DIGITALVOICE', 'C4FM', 'DMR', 'DSTAR') then 'PHONE'
        when upper(mode) in ('FT8', 'FT4') then 'FT8'
        when upper(mode) = 'MFSK' and upper(submode) = 'FT4' then 'FT8'
        else 'DIGI'
    end;
