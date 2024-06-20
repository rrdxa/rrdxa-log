create extension jsquery;

-- qrz: station cty/loc cache

create table rrdxa.qrz (
    ts timestamptz(0) not null default now(),
    dx_cty smallint,
    dx text constraint qrz_pkey primary key,
    dx_cont rrdxa.continent,
    dx_loc text
);

comment on table rrdxa.qrz is 'Station cty/loc cache';

create or replace function rrdxa.qrz_trigger()
    returns trigger
    language plpgsql
as $$
declare
    _cont rrdxa.continent;
begin
    if new.dx_cty is not null and new.dx_cont is null then
        select cont into _cont from rrdxa.dxcc where dxcc = new.dx_cty;
        if _cont is not null then
            new.dx_cont = _cont;
        end if;
    end if;

    return new;
end;
$$;

create trigger qrz_trigger
    before insert or update on rrdxa.qrz
    for each row execute function qrz_trigger();

-- incoming: where gatherers dump spots

create unlogged table rrdxa.incoming (
    source text not null,
    cluster text,
    spot_time timestamptz(0) not null default now(),
    spotter text not null,
    spotter_cty smallint,
    spotter_cont text, -- filled in by incoming_trigger
    spotter_loc text,
    qrg numeric not null,
    band band not null generated always as ((qrg / 1000.0)::band) stored,
    dx text not null,
    dx_cty smallint,
    dx_cont text, -- unused, filed in at the bandmap stage
    dx_loc text,
    mode text,
    db int,
    wpm int,
    info text,
    extra jsonb -- unused, could be used for spotter attributes like rrdxa_member
);

comment on table rrdxa.incoming is 'Where gatherers dump spots';

create or replace function rrdxa.incoming_trigger()
    returns trigger
    language plpgsql
as $$
declare
    _cty text;
    _cont text;
    _loc text;
begin
    if new.spotter_cty is null or new.spotter_cont is null or new.spotter_loc is null then
        select dx_cty, dx_cont, dx_loc into _cty, _cont, _loc from qrz where dx = strip_dash(new.spotter);
        if found then
            if new.spotter_cty is null and _cty is not null then
                new.spotter_cty = _cty;
            end if;
            if new.spotter_cont is null and _cont is not null then
                new.spotter_cont = _cont;
            end if;
            if new.spotter_loc is null and _loc is not null then
                new.spotter_loc = _loc;
            end if;
        end if;
    end if;
    -- dx data is updated in bandmap_trigger

    return new;
end;
$$;

comment on function rrdxa.incoming_trigger is 'Fill in info about the spotting station';

create trigger incoming_trigger
    before insert on rrdxa.incoming
    for each row execute function incoming_trigger();

create unlogged table rrdxa.stats_incoming (
    source text not null,
    cluster text,
    constraint stats_incoming_key unique nulls not distinct (source, cluster),
    first_time timestamptz not null default now(),
    last_time timestamptz not null default now(),
    batches bigint not null default 1,
    spots bigint not null
);

comment on table rrdxa.stats_incoming is 'Spot counts per source/cluster';

-- bandmap: where all spots are stored (aggregated from incoming by gather/incoming)

create unlogged table rrdxa.bandmap (
    spot_time timestamptz not null,
    source text,
    band band,
    dx text,
    data jsonb,
    constraint bandmap_pkey primary key (source, band, dx)
);

create index on rrdxa.bandmap using gin (data jsonb_path_value_ops);

comment on table rrdxa.bandmap is 'Where all spots are stored';

create or replace function rrdxa.cleanup_spots(spot jsonb)
    returns jsonb
    return (with spots as
        (select row_number() over (partition by s->'spotter' order by s->'spot_time' desc), s
            from jsonb_array_elements(spot) s
            where (s->>'spot_time')::timestamp > now() - '30min'::interval),
        spots2 as (select s from spots where row_number = 1 order by s->'spot_time' desc limit 50)
        select jsonb_agg(s) from spots2);

comment on function rrdxa.cleanup_spots is 'Keep only most recent spot per spotter, delete spots older than 30min, keep at most 50 spots';

CREATE OR REPLACE VIEW public.bandmap_v AS
 SELECT spot_time,
    source,
    band,
    (data ->> 'qrg'::text)::numeric AS qrg,
    data ->> 'mode'::text AS mode,
    (data ->> 'wpm'::text)::smallint AS wpm,
    dx,
    (data ->> 'dx_cty'::text)::smallint AS dx_cty,
    (data ->> 'dx_cont'::text)::continent AS dx_cont,
    data ->> 'dx_loc'::text AS dx_loc,
    data['spots'::text] AS spots
   FROM bandmap;

CREATE OR REPLACE VIEW public.spot_v AS
 SELECT (spots.spot ->> 'spot_time'::text)::timestamp with time zone AS spot_time,
    bandmap_v.source,
    spots.spot ->> 'cluster'::text AS cluster,
    bandmap_v.band,
    bandmap_v.qrg,
    bandmap_v.mode,
    bandmap_v.wpm,
    bandmap_v.dx,
    bandmap_v.dx_cty,
    bandmap_v.dx_cont,
    bandmap_v.dx_loc,
    spots.spot ->> 'spotter'::text AS spotter,
    spots.spot ->> 'spotter_cty'::text AS spotter_cty,
    spots.spot ->> 'spotter_cont'::text AS spotter_cont,
    spots.spot ->> 'spotter_loc'::text AS spotter_loc,
    (spots.spot ->> 'db'::text)::smallint AS db,
    spots.spot ->> 'info'::text AS info
   FROM bandmap_v,
    LATERAL jsonb_array_elements(bandmap_v.spots) spots(spot);

create or replace function rrdxa.bandmap_trigger()
    returns trigger
    language plpgsql
as $$
declare
    _cty text;
    _cont text;
    _loc text;
    _basecall text;
    _rroperator text;
begin
    select dx_cty, dx_cont, dx_loc into _cty, _cont, _loc from qrz where dx = new.dx;
    if found then
        if new.data['dx_cty'] is null and _cty is not null then
            new.data['dx_cty'] = to_jsonb(_cty);
        end if;
        if new.data['dx_cont'] is null and _cont is not null then
            new.data['dx_cont'] = to_jsonb(_cont);
        end if;
        if new.data['dx_loc'] is null and _loc is not null then
            new.data['dx_loc'] = to_jsonb(_loc);
            new.data['dx_loc2'] = to_jsonb(_loc::varchar(2));
            new.data['dx_loc4'] = to_jsonb(_loc::varchar(4));
        end if;
    end if;

    _basecall := basecall(new.dx);
    if new.data['rrdxa_member'] is null then
        select rroperator into _rroperator from rrdxa.rrcalls where rrcall = _basecall;
        if found then
            new.data['rrdxa_member'] := to_jsonb(_rroperator);
        end if;
    end if;

    return new;
end;
$$;

comment on function rrdxa.bandmap_trigger is 'Fill in info about the DX station';

create trigger bandmap_trigger
    before insert on rrdxa.bandmap
    for each row execute function bandmap_trigger();

-- rule: notification rules on channels

create or replace function rrdxa.rule_json_to_jsquery(rule jsonb)
    returns text
    immutable
    return (with
        incl_rule as (
            select string_agg(case value
                when 'true' then to_json(key)::text -- true -> key exists check
                else format('(%s in (%s))', to_json(key), substr(value, 2, length(value)-2)) -- array -> match values
                end, ' and ') str
            from jsonb_each_text(rule->'include') where value <> '[]'),
        incl_spots_rule as (
            select string_agg(case value
                when 'true' then to_json(key)::text -- true -> key exists check
                else format('(%s in (%s))', to_json(key), substr(value, 2, length(value)-2)) -- array -> match values
                end, ' and ') str
            from jsonb_each_text(rule->'include_spots') where value <> '[]'),
        excl_rule as (
            select string_agg(case value
                when 'true' then to_json(key)::text
                else format('(%s in (%s))', to_json(key), substr(value, 2, length(value)-2))
                end, ' or ') str
            from jsonb_each_text(rule->'exclude') where value <> '[]')
        select concat_ws(' and ',
            incl_rule.str,
            ('spots.#(' || incl_spots_rule.str || ')'),
            ('not (' || excl_rule.str || ')'))
        from incl_rule, incl_spots_rule, excl_rule);

/*
select rule_json_to_jsquery('{
"include": {
    "dx": ["DF7CB", "DL5VT"],
    "band": ["15m"],
    "rrdxa_member": true},
"include_spots": {
    "spotter_cty": [230],
    "spotter_loc": ["JO31"]},
"exclude": {
    "mode": [],
    "dx_cty": ["123"],
    "foc_member": true}
}'::jsonb);
*/

comment on function rrdxa.rule_json_to_jsquery is 'Transform a filter specification in JSON format to jsquery';

create table rrdxa.rule (
    id int primary key generated always as identity,
    channel text not null,
    timeout interval, -- make these global channel options?
    filter_worked boolean default false,
    filter_cty boolean default false,
    filter_loc boolean default false,
    rule jsonb not null,
    jsfilter jsquery generated always as (rule_json_to_jsquery(rule)::jsquery) stored
);

comment on table rrdxa.rule is 'Notification rules for channels';

-- notification: NOTIFY clients about new spots

create unlogged table rrdxa.notification (
    channel text not null,
    dx text not null,
    band band not null,
    mode text,
    ts timestamptz not null default now(),
    constraint notification_key unique nulls not distinct (channel, dx, band, mode)
);

comment on table rrdxa.notification is 'Cache of sent notifications to implement mute windows';

\ir bandmap_notification.sql

comment on function rrdxa.bandmap_notification is 'Notify clients about new spots';

create trigger bandmap_notification
    after insert or update on rrdxa.bandmap
    for each row execute function bandmap_notification();
