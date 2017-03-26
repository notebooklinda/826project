#!/bin/bash
initdb $HOME/public/826prj
pg_ctl -D $HOME/public/826prj -o '-k /tmp' start
createdb $USER

