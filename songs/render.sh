#!/bin/sh
# render.sh <stem> <body> [tele], in the melody's folder: sings <stem>.json into <stem>.wav (and
# <stem>.tele). Skipped when the melody, body and $CHIMERA are unchanged since its last render.
set -eu
[ $# -le 3 ] && [ "${3:-tele}" = tele ] || { echo "render.sh: bad job: $*" >&2; exit 1; }
stem=$1 body=$2 tele=${3:-}
sig="$body $tele $(cksum < "$stem.json")"
if [ -f "$stem.wav" ] && [ "$(cat "$stem.done" 2>/dev/null)" = "$sig" ] && [ ! "$CHIMERA" -nt "$stem.wav" ] &&
   { [ -z "$tele" ] || [ -f "$stem.tele" ]; }; then
  echo "$stem: up to date"; exit 0
fi
rm -f "$stem.done"
if [ -n "$tele" ]; then
  "$CHIMERA" render notes "$stem.json" "$stem" "$body" --tele "$stem.tele"
else
  "$CHIMERA" render notes "$stem.json" "$stem" "$body"
fi
echo "$sig" > "$stem.done"
