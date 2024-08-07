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

create or replace function rrdxa.jsonb_arraymatch_to_jsquery(key text, arr text)
    returns text
    immutable
    return case when arr = '[]' then '"false"'
        else format('(%s in (%s))', to_jsonb(key), substr(arr, 2, length(arr)-2))
    end;

create or replace function rrdxa.rule_object_to_jsquery(rule jsonb)
    returns text
    immutable
    return (with
        incl_rule as (
            select string_agg(case value
                when 'true' then to_json(key)::text -- true -> key exists check
                else rrdxa.jsonb_arraymatch_to_jsquery(key, value) -- array -> match values
                end, ' and ') str
            from jsonb_each_text(rule->'include') where value <> '[]'),
        incl_spots_rule as (
            select string_agg(case value
                when 'true' then to_json(key)::text -- true -> key exists check
                else rrdxa.jsonb_arraymatch_to_jsquery(key, value) -- array -> match values
                end, ' and ') str
            from jsonb_each_text(rule->'include_spots') where value <> '[]'),
        excl_rule as (
            select string_agg(case value
                when 'true' then to_json(key)::text
                else rrdxa.jsonb_arraymatch_to_jsquery(key, value)
                end, ' or ') str
            from jsonb_each_text(rule->'exclude') where value <> '[]')
        select nullif(concat_ws(' and ',
            incl_rule.str,
            ('spots.#(' || incl_spots_rule.str || ')'),
            ('not (' || excl_rule.str || ')')), '')
        from incl_rule, incl_spots_rule, excl_rule);

create or replace function rrdxa.rule_array_to_jsquery(rule jsonb)
    returns text
    immutable
    return (select string_agg('(' || rrdxa.rule_object_to_jsquery(value) || ')', ' or ')
	from jsonb_array_elements(rule));

comment on function rrdxa.rule_array_to_jsquery is 'Transform a filter specification in JSON format to jsquery';

/*
select rule_array_to_jsquery('{
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

create or replace function rrdxa.rule_create_channel(channel text)
    returns void
    return (insert into rule 
    return jsonb_set(rule, path, (rule #> path) - element);

create or replace function rrdxa.rule_add_entry(p_channel text, p_path text, p_element text)
    returns void
    language plpgsql
as $$
declare
    res jsonb;
    p_arr text[];
    p_jsonb jsonb;
    msg text;
begin
    p_arr := p_path; -- raise warning below when casts fail
    p_jsonb := to_jsonb(p_element);
    select rule #> p_arr into res from rule where channel = p_channel;
    if res is null then
        update rule set rule[p_arr[1]][p_arr[2]][p_arr[3]] = '[]' where channel = p_channel;
    end if;
    update rule set rule = jsonb_insert(rule, p_arr || array['-1'], p_jsonb, true) where channel = p_channel;
exception when others then
    get stacked diagnostics msg := message_text;
    raise warning 'rule_add_entry(%,%,%) failed: %', p_channel, p_path, p_jsonb, msg;
end;
$$;

comment on function rrdxa.rule_add_entry is 'Add new rule element at 3-level path';

create or replace function rrdxa.rule_delete_entry(p_channel text, p_path text)
    returns void
    language plpgsql
as $$
declare
    p_arr text[];
    msg text;
begin
    p_arr := p_path;
    update rule set rule = rule #- p_arr where channel = p_channel;
    update rule set rule = rule #- p_arr[1:3] where channel = p_channel and rule #> p_arr[1:3] = '[]';
    update rule set rule = rule #- p_arr[1:2] where channel = p_channel and rule #> p_arr[1:2] = '{}';
    update rule set rule = rule #- p_arr[1:1] where channel = p_channel and rule #> p_arr[1:1] = '{}';
exception when others then
    get stacked diagnostics msg := message_text;
    raise warning 'rule_delete_entry(%,%) failed: %', p_channel, p_arr, msg;
end;
$$;

comment on function rrdxa.rule_delete_entry is 'Delete rule element at 4-level path';

create table rrdxa.rule (
    channel text primary key,
    timeout interval, -- make these global channel options?
    filter_worked boolean default false,
    filter_cty boolean default false,
    filter_loc boolean default false,
    rule jsonb not null,
    jsfilter jsquery generated always as (rule_array_to_jsquery(rule)::jsquery) stored
);

comment on table rrdxa.rule is 'Notification rules for channels';

create or replace function rrdxa.rule_update_trigger()
    returns trigger
    language plpgsql
as $$
begin
    perform pg_notify('rule_update',
	jsonb_build_object(
	    'channel', to_jsonb(new.channel),
	    'rule', jsonb_build_object(
		'rule', new.rule,
		'timeout', to_jsonb(new.timeout)))::varchar(7999));
    return new;
end;
$$;

create trigger rule_update
    after insert or update on rrdxa.rule
    for each row execute function rule_update_trigger();

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

create unlogged table rrdxa.stats_notification (
    channel text constraint stats_notification_pkey primary key,
    first_time timestamptz not null default now(),
    last_time timestamptz not null default now(),
    notifies bigint not null default 1
);

\ir bandmap_notification.sql

comment on function rrdxa.bandmap_notification is 'Notify clients about new spots';

create trigger bandmap_notification
    after insert or update on rrdxa.bandmap
    for each row execute function bandmap_notification();
