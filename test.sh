# hal run --agent_name "test" --agent_function "test_agent.run" --benchmark "your_benchmark"

# hal-eval --benchmark online_mind2web \
#   --agent_dir agents/SeeAct \
#   --agent_function main.run \
#   --agent_name "SeeAct" \
#   -A model_name=gpt-4o-mini-2024-07-18 \
#   -A evaluator_webjudge_model_name=gpt-4o-mini-2024-07-18 \
#   -A config_path=/fs/ess/PAS1576/tianci/hal-harness/auto_mode.toml \
#   --run_id "SeeAct_test" \
#   --max_concurrent 1
#   # --continue_run \

hal-eval --benchmark online_mind2web \
  --agent_dir agents/Agent-E \
  --agent_function main.run \
  --agent_name "Agent-E" \
  -A model_name=gpt-4o-mini-2024-07-18 \
  -A evaluator_webjudge_model_name=gpt-4o-mini-2024-07-18 \
  -A planner_max_chat_round=60 \
  -A browser_nav_max_chat_round=30 \
  --run_id "Agent-E_test" \
  --max_concurrent 1
  # --continue_run \

# hal-eval --benchmark online_mind2web \
#   --agent_dir agents/browser-use \
#   --agent_function main.run \
#   --agent_name "Browser_Use" \
#   -A model_name=gpt-4o-mini-2024-07-18 \
#   -A evaluator_webjudge_model_name=gpt-4o-mini-2024-07-18 \
#   -A max_steps=2 \
#   --run_id "Browser_Use_test" \
#   --max_concurrent 1
#   # --continue_run \