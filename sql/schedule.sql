create or replace function schedule_events()
    returns void
    language plpgsql
as $$
begin

    -- MWC each Monday
    if extract(dow from now()) = 1 then
        insert into event (event, cabrillo_name, start, stop)
            values ('MWC '||to_char(now(), 'YYMMDD'), 'MWC', 'today 16:30', 'today 17:30');
    end if;

end;
$$;
