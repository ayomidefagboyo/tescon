#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# run_proxy_pipeline_local.sh
# ---------------------------------------------------------------------------
# Runs the FULL proxy-capture pipeline locally on your Mac:
#   1. Queues every matched pending symbol into R2 (one job).
#   2. Processes the queue with rembg in batches of 100 symbols (~300 images)
#      until it is empty — re-queueing the remainder each batch automatically.
#
# Why batches of 100?  local_processor.py self-caps at --daily-limit 100 and
# saves the rest as "<job>_remainder", so a big queue is safe: it gets chewed
# through 100 symbols at a time. There is NO 3-hour limit locally, so this can
# run overnight and clear the whole backlog in one sitting.
#
# Usage:
#   bash run_proxy_pipeline_local.sh           # full queue + process everything
#   Ctrl-C any time to stop; re-run to resume where it left off.
# ---------------------------------------------------------------------------
set -euo pipefail
cd "$(dirname "$0")"   # repo root

BATCH=100
MAX_BATCHES=60         # safety stop (60 x 100 = 6000 symbols)

echo "=============================================================="
echo "STEP 1/2  Queueing all matched pending symbols into R2"
echo "=============================================================="
python3 backend/proxy_capture.py        # full run (no --dry-run)

echo
echo "=============================================================="
echo "STEP 2/2  Processing the queue, ${BATCH} symbols per batch"
echo "=============================================================="
i=0
while true; do
  i=$((i+1))
  echo
  echo "------------------------- batch ${i} -------------------------"
  python3 -u backend/local_processor.py --daily-limit "${BATCH}" 2>&1 | tee .processor_out.log
  if grep -q "No queued jobs found" .processor_out.log; then
    echo
    echo "==> Queue empty — all symbols processed."
    break
  fi
  if [ "${i}" -ge "${MAX_BATCHES}" ]; then
    echo
    echo "==> Safety stop after ${i} batches. Re-run this script to continue."
    break
  fi
done

echo
echo "=============================================================="
echo "DONE.  Optional: refresh the weekly report for your boss with:"
echo "    python3 backend/update_weekly_report.py"
echo "=============================================================="
