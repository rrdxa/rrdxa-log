\ir wp_fdw_vars.sql

create extension if not exists mysql_fdw;
create server if not exists wordpress foreign data wrapper mysql_fdw options ( host :'host' );
create user mapping if not exists for current_user server wordpress options ( username :'user', password :'pass' );

create schema wordpress;
import foreign schema :user limit to ( :"usertable" ) from server wordpress into wordpress;

create materialized view rrdxa.wordpress_users as select * from wordpress.:"usertable";
create index on rrdxa.wordpress_users (upper(user_login));
