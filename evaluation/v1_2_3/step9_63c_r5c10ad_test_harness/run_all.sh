#!/bin/zsh
# Usage: run_all.sh OUTPUT_DIR   (OUTPUT_DIR must be outside the repository)
# Runs every tests/test_*.py module in its own guarded subprocess (Step 9.63c-r5c10ab).
S=${0:A:h}
REPO=${S:h:h:h}
OUT=${1:?output directory required}; mkdir -p $OUT
cd $REPO
export CBTI_GUARD_ROOT=$REPO CBTI_GUARD_LOG=$OUT/guard.jsonl PYTHONPATH=$S/guard PYTHONDONTWRITEBYTECODE=1
export DEEPSEEK_API_KEY=ci-placeholder-no-network OPENAI_API_KEY= ANTHROPIC_API_KEY= TAVILY_API_KEY=
export ENABLE_WEB_SEARCH=false LANGCHAIN_TRACING_V2=false
for f in tests/test_*.py; do
  m=${f:t:r}
  perl -e "alarm shift; exec @ARGV" 900 .venv/bin/python $S/run_module.py $OUT/$m.json $m > $OUT/$m.log 2>&1
  echo "$m exit=$?" >> $OUT/exit_codes.txt
done
echo DONE
