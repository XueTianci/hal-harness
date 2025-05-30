import os
import json
import weave
import time
from typing import Dict, Any, Optional
from .benchmark_manager import BenchmarkManager
from .utils.local_runner import LocalRunner
from .utils.docker_runner import DockerRunner
from .utils.logging_utils import print_step, print_success, print_error, create_progress, console, log_warning, print_warning
import sys
from rich.table import Table
from rich.box import ROUNDED
from .utils.logging_utils import terminal_print
from .inspect.inspect import is_inspect_benchmark
from .utils.weave_utils import get_call_ids, delete_calls,MODEL_PRICES_DICT
class AgentRunner:
    """Handles running agents either locally or on VMs"""

    def __init__(self, 
                 agent_function: str,
                 agent_dir: str,
                 agent_args: Dict[str, Any],
                 benchmark_name: str,
                 config: Dict[str, Any],
                 run_id: Optional[str] = None,
                 use_vm: bool = False,
                 use_docker: bool = False,
                 max_concurrent: int = 1,
                 conda_env: Optional[str] = None,
                 continue_run: bool = False,
                 run_command: str = None,
                 ignore_errors: bool = False,
                 max_tasks: Optional[int] = None):
        
        # Validate agent_function format
        if not isinstance(agent_function, str) or '.' not in agent_function:
            raise ValueError("Invalid agent_function format. Must be in format 'module.function' (e.g., 'my_agent.run_agent')")
        
        module_name, func_name = agent_function.rsplit('.', 1)
        if not module_name or not func_name:
            raise ValueError("Invalid agent_function format. Both module and function names must be non-empty")
        
        # Check for requirements.txt
        requirements_path = os.path.join(agent_dir, 'requirements.txt')
        if not os.path.exists(requirements_path) and not conda_env and not use_docker and not use_vm:
            raise ValueError(f"No requirements.txt found in agent directory: {agent_dir}")
        
        # Validate runner options
        if sum([bool(conda_env), use_vm, use_docker]) > 1:
            raise ValueError("Only one of conda_env, use_vm, or use_docker can be set at a time.")
        
        # Initialize benchmark first
        self.benchmark_manager = BenchmarkManager(agent_dir, config)
        self.benchmark = self.benchmark_manager.get_benchmark(benchmark_name)
        self.benchmark.agent_args = agent_args
        
        # Check if any task requires GPU
        has_gpu_task = False
        if hasattr(self.benchmark, 'benchmark') and isinstance(self.benchmark.benchmark, dict):
            for task_id, task_data in self.benchmark.benchmark.items():
                if isinstance(task_data, dict) and task_data.get('gpu', False):
                    has_gpu_task = True
                    break
        
        # Print warning if GPU tasks are present but not running on VM
        if has_gpu_task and not use_vm:
            print_warning("Warning: This benchmark contains tasks that require GPU, but is not being run on a VM. "
                         "GPU tasks may not work correctly without VM execution. Use the --vm flag to run on a VM.")
        
        self.run_command = run_command
                
        # Check if benchmark requires sandbox
        if self.benchmark.requires_sandbox and not use_vm and not use_docker:
            raise ValueError(f"Benchmark {benchmark_name} requires sandbox execution. Please use --vm or --docker flag.")
        
        
        # Set run ID
        self.run_id = run_id or f"{benchmark_name}_{int(time.time())}"
        
        # Initialize appropriate runner with benchmark
        if use_vm:
            from .utils.vm_runner import VMRunner
            self.runner = VMRunner(
                max_concurrent=max_concurrent,
                log_dir=self.benchmark.get_run_dir(self.run_id),
                benchmark=self.benchmark
            )
        elif use_docker:
            self.runner = DockerRunner(
                max_concurrent=max_concurrent,
                log_dir=self.benchmark.get_run_dir(self.run_id),
                benchmark=self.benchmark
            )
        else:
            self.runner = LocalRunner(
                max_concurrent=max_concurrent,
                conda_env=conda_env,
                log_dir=self.benchmark.get_run_dir(self.run_id),
                benchmark=self.benchmark
            )
        
        self.agent_function = agent_function
        self.agent_dir = agent_dir
        self.agent_args = agent_args
        self.config = config
        self.max_concurrent = max_concurrent
        self.conda_env = conda_env
        self.use_vm = use_vm
        self.use_docker = use_docker
        self.continue_run = continue_run
        self.ignore_errors = ignore_errors
        self.max_tasks = max_tasks
        

    def get_remaining_tasks(self, dataset: Dict[str, Any]) -> Dict[str, Any]:
        """Get tasks that haven't been completed in previous runs"""
            
        # Check for raw submissions file
        run_dir = self.benchmark.get_run_dir(self.run_id)
        submissions_file = os.path.join(run_dir, f"{self.run_id}_RAW_SUBMISSIONS.jsonl")
        
        if not os.path.exists(submissions_file):
            print("No previous submissions found, running all tasks")
            return dataset
            
        try:
            # Load completed tasks from submissions file
            completed_tasks = set()
            previous_output = {}
            with open(submissions_file) as f:
                for line in f:
                    try:
                        submission = json.loads(line.strip())
                        task_id = list(submission.keys())[0]
                        result = submission[task_id]
                        # Only count as completed if not an error
                        if not isinstance(result, str) or not result.startswith("ERROR"):
                            completed_tasks.add(task_id)
                        previous_output.update(submission)
                    except json.JSONDecodeError as e:
                        print_warning(f"Skipping malformed line in submissions file: {e}")
                        continue
            
            # Filter out completed tasks
            remaining_tasks = {
                task_id: data 
                for task_id, data in dataset.items() 
                if task_id not in completed_tasks
            }
            
            return remaining_tasks
            
        except Exception as e:
            print_error(f"Error loading previous submissions: {e}")
            return dataset

    async def run(self, agent_name: str, upload: bool = False) -> Dict[str, Any]:
        """Run the full agent evaluation pipeline"""
        
        # Initialize logging for main run
        print_step("Initializing logging with W&B Weave...")
        weave_client = weave.init(self.run_id)
        
        # Get dataset and filter for remaining tasks if continuing
        dataset = self.benchmark.get_dataset()
        if self.continue_run and not self.ignore_errors:
            dataset = self.get_remaining_tasks(dataset)
        elif self.continue_run and self.ignore_errors:
            dataset = {}
            
        # Limit the number of tasks if max_tasks is specified
        if self.max_tasks and self.max_tasks > 0 and self.max_tasks < len(dataset):
            print_step(f"Limiting to the first {self.max_tasks} tasks as requested")
            task_ids = list(dataset.keys())[:self.max_tasks]
            dataset = {task_id: dataset[task_id] for task_id in task_ids}
            
        # delete previous calls from previous run if continuing for remaining tasks
        if self.continue_run and not self.ignore_errors:
            print_step("Cleaning up calls from previous run...")
            for task_id in dataset:
                call_ids = get_call_ids(task_id, weave_client)
                if len(call_ids) > 0:
                    delete_calls(call_ids, weave_client)
        
        if not dataset:
            print_warning("No remaining tasks to run")
            # Load and return previous results
            results_path = os.path.join(self.benchmark.get_run_dir(self.run_id), f"{self.run_id}_UPLOAD.json")
            if os.path.exists(results_path):
                print_step("Loading previous results...")
                with open(results_path) as f:
                    previous_results = json.load(f)
                return previous_results["results"]
            else:
                print_step("No previous results found. Running evaluation harness on previous raw submissions...")
                # If continuing run, merge with previous results
                agent_output = {}
                results_path = os.path.join(self.benchmark.get_run_dir(self.run_id), f"{self.run_id}_RAW_SUBMISSIONS.jsonl")
                if os.path.exists(results_path):
                    previous_output = {}
                    with open(results_path) as f:
                        for line in f:
                            submission = json.loads(line.strip())
                            previous_output.update(submission)
                    agent_output.update(previous_output)
            
        else:
            if "browser-use" in self.agent_dir and ("gemini" or "deepseek" in self.agent_args["model_name"]):
                if "gemini" in self.agent_args["model_name"]:
                    weave_client.add_cost(
                            llm_id=f"models/{self.agent_args['model_name']}",
                            prompt_token_cost=MODEL_PRICES_DICT[self.agent_args["model_name"]]["prompt_tokens"],
                            completion_token_cost=MODEL_PRICES_DICT[self.agent_args["model_name"]]["completion_tokens"]
                        )
                else:
                    weave_client.add_cost(
                            llm_id=self.agent_args['model_name'],
                            prompt_token_cost=MODEL_PRICES_DICT[self.agent_args["model_name"]]["prompt_tokens"],
                            completion_token_cost=MODEL_PRICES_DICT[self.agent_args["model_name"]]["completion_tokens"]
                        )
            # Run agent on all tasks
            with create_progress() as progress:
                task = progress.add_task("Running agents... (check logs in results directory for more details)", total=len(dataset))
                agent_output = await self.runner.run_agent(
                    dataset=dataset,
                    agent_function=self.agent_function,
                    agent_dir=self.agent_dir,
                    agent_args=self.agent_args,
                    run_id=self.run_id,
                    benchmark=self.benchmark,
                    task=task,
                    progress=progress   
                )
            
            # If continuing run, merge with previous results
            if self.continue_run:
                results_path = os.path.join(self.benchmark.get_run_dir(self.run_id), f"{self.run_id}_RAW_SUBMISSIONS.jsonl")
                if os.path.exists(results_path):
                    previous_output = {}
                    with open(results_path) as f:
                        for line in f:
                            try:
                                submission = json.loads(line.strip())
                                previous_output.update(submission)
                            except json.JSONDecodeError as e:
                                print_warning(f"Skipping malformed line in submissions file: {e}")
                                continue
                    agent_output.update(previous_output)
        
        print_step("Evaluating results...")
        # Create a temporary dataset with agent_output to check remaining tasks
        remaining = self.get_remaining_tasks(dataset)
        if len(remaining) > 0:
            # Create a more informative error message
            print_warning(f"Warning - {len(remaining)} tasks are incomplete")
            
            # Create and display table of remaining tasks
            table = Table(title="Incomplete Tasks", show_header=True, box=ROUNDED)
            table.add_column("Task ID", style="cyan")
            
            for task_id, task_data in remaining.items():
                table.add_row(task_id)
            
            with terminal_print():
                console.print(table)
            
            print_step("Use --continue-run flag to retry the remaining tasks. Exiting...")
            # sys.exit(1)
            
        # stop weave logging before harness is run to avoid lm as judge to produce additional cost 
        weave.finish()
        
        if is_inspect_benchmark(self.benchmark.benchmark_name):
            eval_results = await self.benchmark.evaluate_output(agent_output, self.run_id)
        else:
            eval_results = self.benchmark.evaluate_output(agent_output, self.run_id)
        
        print_step("Processing results...")
        results = self.benchmark.process_results(
            agent_name=agent_name,
            run_id=self.run_id,
            agent_args=self.agent_args,
            run_command=self.run_command,
            eval_results=eval_results,
            weave_client=weave_client,
            upload=upload
        )
        return results
