-- refresh passwords
refresh materialized view rrdxa.wordpress_users;

-- delete uploads that have no QSOs
delete from rrdxa.upload where ts < now() - '1 week'::interval and
id not in (with recursive upload_ids as (
        select min(upload) from rrdxa.log
        union all
        select (select min(upload) from rrdxa.log where upload > upload_ids.min) from upload_ids where upload_ids.min is not null
)
select * from upload_ids where min is not null);
