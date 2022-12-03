Rhein Ruhr DX Association Logbook
=================================

## Required packages

```
PGVERSION=15
sudo apt install \
  postgresql-$PGVERSION \
  postgresql-$PGVERSION-mysql-fdw \
  postgresql-$PGVERSION-partman \
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
