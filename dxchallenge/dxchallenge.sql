begin;

\echo New DXCC
select major_mode, dxcc, array_agg(row_to_json(b)) from bandpoints b
    where year = 2024 and
    not exists (select from previous_bandpoints pb where b.major_mode = pb.major_mode and b.dxcc = pb.dxcc and year = 2024)
    group by major_mode, dxcc;

\echo New bandpoints
select major_mode, dxcc, band, array_agg(row_to_json(b)) from bandpoints b
    where year = 2024 and
    not exists (select from previous_bandpoints pb where b.major_mode = pb.major_mode and b.dxcc = pb.dxcc and b.band = pb.band and year = 2024)
    group by major_mode, dxcc, band;

\echo New DXers
select major_mode, rrmember, array_agg(row_to_json(b)) from bandpoints b
    where year = 2024 and
    not exists (select from previous_bandpoints pb where b.major_mode = pb.major_mode and b.rrmember = pb.rrmember and year = 2024)
    group by major_mode, rrmember;

\echo Most wanted countries
select major_mode, dxcc, count(*) from bandpoints group by major_mode, dxcc order by major_mode, count(*), dxcc;

\echo Most wanted bandslots
select major_mode, dxcc, band, count(*) from bandpoints group by major_mode, dxcc, band order by major_mode, count(*), dxcc, band;

\echo Bandpoints gained
select major_mode, rrmember, dxcc, band, array_agg(row_to_json(b)) from bandpoints b
    where year = 2024 and
    not exists (select from previous_bandpoints pb where b.major_mode = pb.major_mode and b.rrmember = pb.rrmember and b.dxcc = pb.dxcc and b.band = pb.band and year = 2024)
    group by major_mode, rrmember, dxcc, band;

delete from previous_bandpoints;
insert into previous_bandpoints select * from bandpoints;

insert into bandpoints_history
select 'yesterday'::date, rrmember, major_mode, band, count(distinct dxcc), array_agg(distinct dxcc)
    from bandpoints
    where year = extract(year from 'yesterday'::date)
    group by grouping sets((rrmember, major_mode), (rrmember, major_mode, band));

commit;
