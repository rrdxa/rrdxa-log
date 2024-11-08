-- refresh member list (including passwords)
refresh materialized view rrdxa.wordpress_users;
refresh materialized view rrdxa.members;
refresh materialized view rrdxa.rrcalls;

-- refresh pre-calculated data
refresh materialized view rrdxa.rrdxa60_top;
refresh materialized view rrdxa.bandpoints;

-- delete uploads that have no QSOs
delete from rrdxa.upload where ts < now() - '4 week'::interval and
id not in (with recursive upload_ids as (
        select min(upload) from rrdxa.log
        union all
        select (select min(upload) from rrdxa.log where upload > upload_ids.min) from upload_ids where upload_ids.min is not null
)
select * from upload_ids where min is not null);

-- delete events with no logs after 2 weeks
delete from rrdxa.event e where start < now() - '2 weeks'::interval and
    created < now() - '2 weeks'::interval and
    not exists (select from upload u where e.event_id = u.event_id);
