Rhein Ruhr DX Association Logbook
=================================

## Required packages

```
PGVERSION=15
sudo apt install \
  postgresql-$PGVERSION \
  postgresql-$PGVERSION-mysql-fdw \
  postgresql-plpython3-$PGVERSION \
  python3-django \
  python3-passlib \
  python3-psycopg2 \
  python3-pyhamtools \
  python3-requests
```

## Installation

```
$ psql
postgres =# create user "www-data";
postgres =# create database rrdxa;
postgres =# \c rrdxa
rrdxa =# \i sql/00import.sql
```

## Uninstallation

```
$ psql rrdxa
rrdxa =# drop schema rrdxa, wordpress cascade;
```

## Log upload using curl

```
curl -fsS --output /dev/null \
  --user DL1ABC:rrdxaorgpassword \
  --form station_callsign=DL0ABC \
  --form operator=DL1ABC \
  --form contest=CQ-WW-DX \
  --form logfile=@cqwwdx_dl0abc_dl1abc.adif \
  https://logbook.rrdxa.org/log/upload/
```
