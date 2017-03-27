#!/bin/bash
initdb /tmp/pg_db
pg_ctl -D /tmp/pg_db -o '-k /tmp' start
createdb $USER

