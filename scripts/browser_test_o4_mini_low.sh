evaluator_webjudge_model_name=o4-mini-2025-04-16


model_name=o4-mini-2025-04-16
hal-eval --benchmark online_mind2web \
  --agent_dir agents/browser-use \
  --agent_function main.run \
  --agent_name "Browser-Use(o4-mini-2025-04-16_low_reasoning_effort)" \
  -A model_name=${model_name} \
  -A evaluator_webjudge_model_name=${evaluator_webjudge_model_name} \
  -A max_steps=30 \
  -A reasoning_effort="low" \
  --run_id "browser-use_o4-mini_reasoning_effort_low" \
  --max_concurrent 1 \
  --continue_run

