#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

BATCH=100
MAX_BATCHES=60

echo "=============================================================="
echo "Processing the queue, ${BATCH} symbols per batch"
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
echo "DONE."
echo "=============================================================="
