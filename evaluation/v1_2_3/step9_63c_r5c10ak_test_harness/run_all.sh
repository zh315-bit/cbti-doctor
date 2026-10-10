#!/bin/zsh
# Usage: run_all.sh OUTPUT_DIR   (OUTPUT_DIR must be outside the repository)
# Runs every tests/test_*.py module in its own guarded subprocess (Step 9.63c-r5c10ab); r5c10ak copy: every
# module process also installs the session-level hard guard (tests/session_safety.py), and a session
# that the hard guard stops shows up as exit=86.
S=${0:A:h}
REPO=${S:h:h:h}
OUT=${1:?output directory required}; mkdir -p $OUT
cd $REPO
# Step 0: the guard's own negative catalogue runs OUTSIDE any guard (it must spawn children whose
# environment differs from ours, which the guard itself forbids); the test module verifies this output.
.venv/bin/python $S/guard_negative_scenarios.py --guard-dir $S/guard --name harness_guard --out $OUT/guard_negative_live.json > $OUT/guard_negative_live.log 2>&1
echo "guard_negative_catalogue exit=$?" >> $OUT/exit_codes.txt
export CBTI_GUARD_NEGATIVE_RESULTS=$OUT/guard_negative_live.json
export CBTI_GUARD_ROOT=$REPO CBTI_GUARD_LOG=$OUT/guard.jsonl PYTHONPATH=$S/guard PYTHONDONTWRITEBYTECODE=1
export DEEPSEEK_API_KEY=ci-placeholder-no-network OPENAI_API_KEY= ANTHROPIC_API_KEY= TAVILY_API_KEY=
export ENABLE_WEB_SEARCH=false LANGCHAIN_TRACING_V2=false
for f in tests/test_*.py; do
  m=${f:t:r}
  perl -e "alarm shift; exec @ARGV" 900 .venv/bin/python $S/run_module.py $OUT/$m.json $m > $OUT/$m.log 2>&1
  echo "$m exit=$?" >> $OUT/exit_codes.txt
done
echo DONE
