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

create materialized view rrdxa.wordpress_users as select * from wordpress.:"usertable";
create index on rrdxa.wordpress_users (upper(user_login));
analyze rrdxa.wordpress_users;

create or replace function user_roles(capabilities text)
    returns text[]
    language sql
    return
        (select array_agg(r[1] order by r[1]) from regexp_matches(capabilities, '(?<=")([\w]*)(?=")', 'g') rm(r));

create materialized view rrdxa.members as
select
    upper(user_login) as call,
    regexp_split_to_array(upper(x_callsigns.value), '([\s,-]|&amp;)+', 'i') as callsigns,
    display_name,
    m_firstname.meta_value as first_name,
    m_lastname.meta_value as last_name,
    m_nickname.meta_value as nickname,
    user_email,
    user_pass,
    user_roles(m_roles.meta_value)
from wordpress."L7l2a_users" u
left join wordpress."L7l2a_bp_xprofile_data" x_callsigns on u."ID" = x_callsigns.user_id and x_callsigns.field_id = 2
left join wordpress."L7l2a_usermeta" m_firstname on u."ID" = m_firstname.user_id and m_firstname.meta_key = 'first_name'
left join wordpress."L7l2a_usermeta" m_lastname on u."ID" = m_lastname.user_id and m_lastname.meta_key = 'last_name'
left join wordpress."L7l2a_usermeta" m_nickname on u."ID" = m_nickname.user_id and m_nickname.meta_key = 'nickname'
left join wordpress."L7l2a_usermeta" m_roles on u."ID" = m_roles.user_id and m_roles.meta_key = 'L7l2a_capabilities'
order by user_login;

create index on rrdxa.members (call);
analyze rrdxa.members;

commit;
