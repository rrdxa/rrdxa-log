Rhein Ruhr DX Association Logbook
=================================

## Required packages

```
PGVERSION=16
sudo apt install \
  postgresql-$PGVERSION \
  postgresql-$PGVERSION-mysql-fdw \
  postgresql-plpython3-$PGVERSION \
  python3-django \
  python3-paho-mqtt \
  python3-passlib \
  python3-psycopg2 \
  python3-pyhamtools \
  python3-requests \
  \
  daphne \
  python3-django-channels \
  python3-channels-redis \
  redis-server \
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

## Copyright

Copyright (C) 2022-2024 RRDXA

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
