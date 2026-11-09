#!/bin/sh
# A duet show as an MP4 on this machine's GPU (Metal on a Mac): builds the app, serves it, captures, stops.
# usage: tools/show-video.sh <show-id> [out.mp4] [duet-video options, e.g. --fps 30 --size 1920x1080]
# Needs the show in public/shows/<id>/, Bun, ffmpeg, and Google Chrome (or CHROME=/path/to/chromium).
set -eu
cd "$(dirname "$0")/.."
id=${1:?usage: tools/show-video.sh <show-id> [out.mp4] [options]}
out=${2:-$id.mp4}
[ $# -ge 2 ] && shift 2 || shift $#
[ -f "public/shows/$id/show.json" ] || { echo "no show public/shows/$id/show.json" >&2; exit 1; }
cores=$(nproc 2>/dev/null || sysctl -n hw.ncpu)
workers=$(( cores > 4 ? 4 : cores ))
bun install --frozen-lockfile >/dev/null
bun run build >/dev/null
port=5318
bunx vite preview --host 127.0.0.1 --port $port --strictPort >/dev/null 2>&1 &
server=$!
trap 'kill $server 2>/dev/null' EXIT
until curl -sf "http://127.0.0.1:$port/shows/$id/show.json" >/dev/null; do sleep 0.5; done
bun tools/duet-video.ts "$id" "$out" --url "http://127.0.0.1:$port/" --workers "$workers" --gpu "$@"
