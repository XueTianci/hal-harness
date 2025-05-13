evaluator_webjudge_model_name=o4-mini-2025-04-16


model_name=claude-3-7-sonnet-20250219
hal-eval --benchmark online_mind2web \
  --agent_dir agents/browser-use \
  --agent_function main.run \
  --agent_name "Browser-Use_test(claude-3-7-sonnet-20250219)" \
  -A model_name=${model_name} \
  -A evaluator_webjudge_model_name=${evaluator_webjudge_model_name} \
  -A max_steps=30 \
  --run_id "browser-use_claude-3-7-sonnet-20250219" \
  --max_concurrent 1 \
  --continue_run
