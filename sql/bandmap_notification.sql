create or replace function rrdxa.bandmap_notification()
    returns trigger
    language plpgsql
as $$
declare
    n_channel text;
    n_timeout interval;
    n_filter_worked boolean;
    n_filter_cty boolean;
    n_filter_loc boolean;
    worked_dx boolean;
    worked_cty boolean;
    worked_loc boolean;
    n_major_mode mode_t;
    n_ts timestamptz;
    data jsonb;
begin
    for n_channel, n_timeout, n_filter_worked, n_filter_cty, n_filter_loc in
        select channel, max(timeout), min(filter_worked::int), min(filter_cty::int), min(filter_loc::int)
        from rrdxa.rule where new.data @@ jsfilter
        group by channel
    loop
        n_major_mode := major_mode(new.data->>'mode');

        -- when requested, skip spots about stations that were worked before
        select into worked_dx exists(select from log
            where station_callsign = n_channel and call = new.dx and band = new.band and major_mode = n_major_mode);
        if worked_dx and n_filter_worked then continue; end if;
        if new.data['dx_cty'] is not null then
            select into worked_cty exists(select from log
                where station_callsign = n_channel and dxcc = (new.data->>'dx_cty')::smallint and band = new.band and major_mode = n_major_mode);
            if worked_cty and n_filter_cty then continue; end if;
        end if;
        if new.data['dx_loc'] is not null then
            select into worked_loc exists(select from log
                where station_callsign = n_channel and band = new.band and major_mode = n_major_mode
                    and gridsquare >= new.data['dx_loc']::varchar(4) and gridsquare < inc_str(new.data['dx_loc']::varchar(4)));
            if worked_loc and n_filter_loc then continue; end if;
        end if;

        -- when timeout is set, check if we notified about this dx/band/mode already
        if n_timeout is not null then
            insert into notification (channel, dx, band, mode)
                values (n_channel, new.dx, new.band, n_major_mode)
                on conflict on constraint notification_key
                    do update set ts = now() where notification.ts < now() - n_timeout::interval
                returning ts into n_ts;
        end if;

        -- if no timeout is set, or the spot is new or the timeout has lapsed, notify
        if n_timeout is null or n_ts is not null then
            data := new.data;
            data['worked_dx'] = to_jsonb(worked_dx);
            data['worked_cty'] = to_jsonb(worked_cty);
            data['worked_loc'] = to_jsonb(worked_loc);
            data['spots'] = jsonb_build_array(data['spots'][0]);
            perform pg_notify(n_channel, jsonb_strip_nulls(data)::varchar(7999));
            perform pg_notify('spot', jsonb_build_object(
                    'channel', to_jsonb(n_channel),
                    'spot', jsonb_strip_nulls(data)
                )::varchar(7999));
        end if;
    end loop;

    return new;
end;
$$;
