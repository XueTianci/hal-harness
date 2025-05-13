evaluator_webjudge_model_name=o4-mini-2025-04-16


model_name=o3-2025-04-16
hal-eval --benchmark online_mind2web \
  --agent_dir agents/SeeAct \
  --agent_function main.run \
  --agent_name "SeeAct(o3-2025-04-16)" \
  -A model_name=${model_name} \
  -A evaluator_webjudge_model_name=${evaluator_webjudge_model_name} \
  -A config_path=/fs/ess/PAS1576/tianci/hal-harness/agents/SeeAct/model_config_files/o3-2025-04-16.toml \
  --run_id "seeact_o3-2025-04-16" \
  --max_concurrent 1 \
  --continue_run
