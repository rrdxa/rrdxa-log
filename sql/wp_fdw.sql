\ir wp_fdw_vars.sql

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

create materialized view rrdxa.members as
select
    upper(user_login) as call,
    regexp_split_to_array(upper(x_callsigns.value), '[\s,]+') as callsigns,
    display_name,
    user_pass
from wordpress."L7l2a_users" u
left join wordpress."L7l2a_bp_xprofile_data" x_callsigns on u."ID" = x_callsigns.user_id and x_callsigns.field_id = 2
order by user_login;

create index on rrdxa.members (call);
analyze rrdxa.members;

-- select user_id, meta_key, meta_value from wordpress."L7l2a_usermeta" where meta_key in ('nickname', 'first_name', 'last_name', 'last_activity') \crosstabview
