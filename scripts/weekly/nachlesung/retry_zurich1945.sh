#!/bin/bash
# Zürich 1945: 20 Seiten der beiden Teile, deren Lesung ohne Schlusszeile endete (18× finish=stop, 2× length),
# neu lesen. Temperatur 0 gibt bei gleicher Eingabe dasselbe Ergebnis, darum andere Vergrösserung und 32000 Tokens.
# Je Runde nur die noch offenen Seiten; 2 Worker (neben dem Wochenlauf). Ergebnis je Runde in retry/x<Faktor>/.
#   nohup ./retry_zurich1945.sh >> full/zurich1945/retry.log 2>&1 &
set -a; . /home/dh/agentic_historian/.env.gpustack 2>/dev/null; set +a
cd /home/dh/adressbuch_qwen
dir=full/zurich1945; R=$dir/retry
PAGES="58 67 74 222 246 262 373 494 501 576 603 646 723 742 1186 1195 1506 1516 1562 1598"
ts() { TZ=Europe/Zurich date "+%d.%m %H:%M"; }
spec=$(for p in $PAGES; do printf "%s-%s," $p $p; done); spec=${spec%,}
python3 fetch_iiif.py --volume 1945 --width 1010 --pages "$spec" --table iiif_pages.csv --out "$R/pages" || { echo "$(ts) FETCH FAILED"; exit 1; }
for x in 2 2.2 1.8 2.5 1.6; do
  todo=()
  for p in $PAGES; do
    s=$(printf "zurich1945_p%03d" $p)
    grep -lq '"ended": true' $R/x*/${s}_x*.json 2>/dev/null || todo+=("$R/pages/$s.jpeg")
  done
  echo "$(ts) Runde x$x: offen ${#todo[@]}"
  (( ${#todo[@]} )) || break
  python3 run_qwen.py --max-tokens 32000 --workers 2 --upscale $x --out "$R/x$x" "${todo[@]}"
done
echo "$(ts) retry done"
