#!/bin/sh
# Flatulence: a physical model. The Bestiary's flatulence creature plays each of its calls, then
# three held notes with physical courses and two seated on the toilet (script.json), as a creature
# show: ?show=flatulence, and public/shows/flatulence-show.tar.gz to hand over. No score, nothing
# copyrighted.
# Usage: songs/flatulence/make.sh [--no-render]
set -eu
SONG_PY=0
. "$(dirname "$0")/../lib.sh"
[ "$RENDER" = 1 ] || { echo "--no-render: nothing to prepare; the script is $HERE/script.json"; exit 0; }

"$CHIMERA" render creature-show "$HERE/script.json" "$OUT/flatulence" --tele "$OUT/flatulence.ctele"
install_show flatulence "$OUT/flatulence.wav" "$OUT/flatulence.ctele" <<J
{ "title": "Flatulence: a physical model", "audio": "flatulence.wav",
  "creature": "flatulence", "tele": "flatulence.ctele" }
J
(cd "$ROOT/public/shows" && tar czf flatulence-show.tar.gz flatulence)
echo "packed public/shows/flatulence-show.tar.gz"
