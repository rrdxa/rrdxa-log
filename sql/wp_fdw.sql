begin;

\set host rrdxa.org
\set user xxx
\set pass xxx
\set usertable L7l2a_users

create schema wordpress;
set local search_path = wordpress;

create extension if not exists mysql_fdw;
create server if not exists wordpress foreign data wrapper mysql_fdw options ( host :'host' );
create user mapping if not exists for current_user server wordpress options ( username :'user', password :'pass' );

create schema wordpress;
import foreign schema :user limit to ("L7l2a_users") from server wordpress into wordpress;
import foreign schema :user limit to ("L7l2a_usermeta") from server wordpress into wordpress;
import foreign schema :user limit to ("L7l2a_bp_xprofile_data") from server wordpress into wordpress;

create or replace function rrdxa.user_roles(capabilities text)
    returns text[]
    language sql
    return
        (select array_agg(r[1] order by r[1]) from regexp_matches(capabilities, '(?<=")([\w]*)(?=")', 'g') rm(r));

create materialized view rrdxa.members as
select
    upper(user_login) as call,
    regexp_split_to_array(upper(x_callsigns.value), '([\s,-]|&amp;)+', 'i') as callsigns,
    x_member_no.value::int as member_no,
    display_name,
    m_firstname.meta_value as first_name,
    m_lastname.meta_value as last_name,
    m_nickname.meta_value as nickname,
    user_email,
    user_pass,
    "ID" as wpid,
    user_roles(m_roles.meta_value),
    not '{bbp_spectator}' <@ user_roles(m_roles.meta_value) as public,
    '{administrator}' <@ user_roles(m_roles.meta_value) as admin
from wordpress."L7l2a_users" u
left join wordpress."L7l2a_bp_xprofile_data" x_callsigns on u."ID" = x_callsigns.user_id and x_callsigns.field_id = 2
left join wordpress."L7l2a_bp_xprofile_data" x_member_no on u."ID" = x_member_no.user_id and x_member_no.field_id = 3
left join wordpress."L7l2a_usermeta" m_firstname on u."ID" = m_firstname.user_id and m_firstname.meta_key = 'first_name'
left join wordpress."L7l2a_usermeta" m_lastname on u."ID" = m_lastname.user_id and m_lastname.meta_key = 'last_name'
left join wordpress."L7l2a_usermeta" m_nickname on u."ID" = m_nickname.user_id and m_nickname.meta_key = 'nickname'
left join wordpress."L7l2a_usermeta" m_roles on u."ID" = m_roles.user_id and m_roles.meta_key = 'L7l2a_capabilities'
order by user_login;

create unique index on rrdxa.members (call);
create unique index on rrdxa.members (member_no);
analyze rrdxa.members;

create materialized view rrdxa.rrcalls as
select call as rrcall, call as rroperator from members where call ~ '[0-9]' and public
union
select u, call from members, unnest(callsigns) u(u) where call ~ '[0-9]' and public
order by 2, 1;

create unique index on rrdxa.rrcalls(rrcall);
create index on rrdxa.rrcalls(rroperator);
analyze rrdxa.rrcalls;

commit;
