evaluator_webjudge_model_name=o4-mini-2025-04-16


model_name=gemini/gemini-2.5-pro-preview-03-25
hal-eval --benchmark online_mind2web \
  --agent_dir agents/SeeAct \
  --agent_function main.run \
  --agent_name "SeeAct(gemini-2.5-pro-preview-03-25)" \
  -A model_name=${model_name} \
  -A evaluator_webjudge_model_name=${evaluator_webjudge_model_name} \
  -A config_path=/fs/ess/PAS1576/tianci/hal-harness/agents/SeeAct/model_config_files/gemini-2.5-pro-preview-03-25.toml \
  --run_id "seeact_gemini-2.5-pro-preview-03-25" \
  --max_concurrent 1 \
  --continue_run
