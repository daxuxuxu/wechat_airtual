#!/usr/bin/env bash
set -euo pipefail

xrun \
  -f snippets/compfiles.f \
  -f snippets/compopts.f \
  -f snippets/elabopts.f \
  -f snippets/runopts.f \
  +UVM_TESTNAME=smoke_test \
  +ntb_random_seed=20260722 \
  -l logs/smoke_seed20260722.log
