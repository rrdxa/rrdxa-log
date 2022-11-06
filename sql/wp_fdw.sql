create extension mysql_fdw;
create server wordpress foreign data wrapper mysql_fdw options ( host :'host' );
create user mapping for current_user server wordpress options ( username :'user', password :'pass' );
create schema wordpress;
import foreign schema :user limit to ( :"usertable" ) from server wordpress into wordpress;
create materialized view rrdxa.wordpress_users as select * from wordpress.:"usertable";
