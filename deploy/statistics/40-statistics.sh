#!/bin/sh
# Collection is asynchronous; a statistics error must not stop the public website.
(
  umask 077
  while :; do
    python3 /opt/ducknap-statistics/server.py
    echo 'Statistics process stopped; retrying in 5 seconds' >&2
    sleep 5
  done
) &
