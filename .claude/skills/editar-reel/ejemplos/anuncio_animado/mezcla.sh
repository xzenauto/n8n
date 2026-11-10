#!/bin/bash
# Uso: mezcla.sh dir_render voz.wav salida.mp4
set -e
R=$1; VOZ=$2; OUT=$3
E=/home/user/n8n/.claude/skills/editar-reel/ejemplos
DUR=$(python3 -c "import json;print(json.load(open('$R/video.mkv.events.json'))['end'])")
POPS=$(python3 -c "import json;print(' '.join(str(x) for x in json.load(open('$R/video.mkv.events.json'))['pops']))")
WH=$(python3 -c "import json;print(' '.join(str(round(x,2)) for x in json.load(open('$R/video.mkv.events.json'))['whoosh']))")
python3 -I $E/sfx_pop.py $DUR $R/pops.wav $POPS
python3 -I $E/sfx_whoosh.py $DUR $R/whoosh.wav $WH
ffmpeg -y -loglevel error -i $R/video.mkv -i $VOZ -i $R/musica.wav -i $R/pops.wav -i $R/whoosh.wav -filter_complex \
"[1:a]aresample=48000,pan=stereo|c0=c0|c1=c0,apad,asplit=2[v][vsc];\
[2:a]volume=0.065[m];[m][vsc]sidechaincompress=threshold=0.015:ratio=4:attack=30:release=450[md];\
[3:a]volume=0.10[p];[4:a]volume=0.09[w];\
[v][md][p][w]amix=inputs=4:normalize=0:duration=first,atrim=0:$DUR,loudnorm=I=-14:TP=-1.0:LRA=11,aresample=48000[a]" \
-map 0:v -map "[a]" -c:v libx264 -crf 15 -preset slow -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart -t $DUR $OUT
echo "ok $OUT"
