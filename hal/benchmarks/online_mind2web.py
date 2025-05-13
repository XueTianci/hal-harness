from .base_benchmark import BaseBenchmark
from .Online_Mind2Web.WebJudge import WebJudge_Online_Mind2Web_eval
from .Online_Mind2Web.utils import OpenaiEngine, extract_predication
from typing import Dict, Any, Tuple
import os
import json
from datasets import load_dataset
import copy
import re
import multiprocessing
import asyncio


class OnlineMind2WebBenchmark(BaseBenchmark):
    def __init__(self, agent_dir: str, config: Dict[str, Any], agent_args: Dict[str, Any]) -> None:
        self.benchmark_name = "online_mind2web"
        self.setup_script = ''
        self.requires_sandbox = False
        self.score_threshold = 3
        self.num_workers = 30
        self.agent_args = agent_args

        # Load the dataset
        ds = load_dataset("osunlp/Online-Mind2Web", split="test")
        self.benchmark = {}
        for task in ds:
            task_id = str(task["task_id"])
            self.benchmark[task_id] = {
                "confirmed_task": task["confirmed_task"],
                "website": task["website"],
                "level": task["level"],
                "reference_length": task["reference_length"]
            }

        super().__init__(agent_dir, config, requires_sandbox=self.requires_sandbox, setup_script=self.setup_script)


    def evaluate_output(self, agent_output: Dict[str, Any], run_id: str) -> Dict[str, Any]:
        """Evaluate agent outputs using the WebJudge evaluator."""
        with multiprocessing.Pool(processes=self.num_workers) as pool:
            task_items = list(agent_output.items())
            task_inputs = [
                (task_item, run_id, self.benchmark, self.agent_args, self.score_threshold)
                for task_item in task_items
            ]
            results = pool.starmap(self._evaluate_single_output, task_inputs)

        eval_results = {task_id: result for task_id, result in results}
        return eval_results
        
        # eval_results = {}
        # return eval_results


    @staticmethod
    def _evaluate_single_output(task_tuple, run_id, benchmark, agent_args, score_threshold) -> Tuple[str, Dict[str, Any]]:
        task_id, results_path = task_tuple
        try:
            if task_id not in benchmark.keys():
                raise ValueError(f"Task {task_id} not found in benchmark.")
            
            print(f"Evaluating task {task_id}...")
            print(f"Results path: {results_path}")
            trajectory_path = results_path["trajectory"].replace("RUN_ID", run_id)
            content_path = results_path["result_file"].replace("RUN_ID", run_id)
            task_description = benchmark[task_id]["confirmed_task"]
            website = benchmark[task_id]["website"]
            level = benchmark[task_id]["level"]
            reference_length = benchmark[task_id]["reference_length"]

            trajectory_image_paths = sorted(
                os.listdir(trajectory_path), key=lambda x: int(re.findall(r'\d+', x)[0])
            )
            trajectory_image_paths = [os.path.join(trajectory_path, p) for p in trajectory_image_paths]

            with open(content_path) as f:
                result = json.load(f)
                output_results = copy.deepcopy(result)
                action_history = result["action_history"]

            model = OpenaiEngine(model=agent_args["evaluator_webjudge_model_name"])

            messages, text, system_msg, record, key_points = WebJudge_Online_Mind2Web_eval(
                task_description, action_history, trajectory_image_paths, model, score_threshold
            )

            response = model.generate(messages)[0]
            predicted_label = extract_predication(response)

            output_results.update({
                "task_id": task_id,
                "confirmed_task": task_description,
                "website": website,
                "level": level,
                "reference_length": reference_length,
                "input_text": text,
                "system_msg": system_msg,
                "evaluation_details": {"response": response, "predicted_label": predicted_label},
                "predicted_label": predicted_label,
                "image_judge_record": record,
                "key_points": key_points
            })

            return task_id, output_results
        except Exception as e:
            print(f"Error evaluating task {task_id}: {e}")
            return task_id, {
                "task_id": task_id,
                "confirmed_task": benchmark[task_id]["confirmed_task"],
                "website": benchmark[task_id]["website"],
                "level": benchmark[task_id]["level"],
                "reference_length": benchmark[task_id]["reference_length"],
                "predicted_label": "unknown",
                "error": str(e)
            }


    def get_metrics(self, eval_results: Dict[str, Any]) -> Dict[str, Any]:
        # overall tallies
        successful_tasks, failed_tasks = [], []
        level_correct_count = {
            'easy': {"success": 0, "total": 0},
            'medium': {"success": 0, "total": 0},
            'hard': {"success": 0, "total": 0}
        } 

        total_tasks = len(eval_results.keys())

        for task_id, eval_result in eval_results.items():
            level = eval_result.get("level", "unknown")
            predicated_label = eval_result.get("predicted_label", "unknown")

            level_correct_count[level]["total"] += 1
            if predicated_label == 1:
                successful_tasks.append(task_id)
                level_correct_count[level]["success"] += 1
            else:
                failed_tasks.append(task_id)

        accuracy = len(successful_tasks) / total_tasks if total_tasks > 0 else 0.0
        metrics = {
            "accuracy": accuracy,
            "successful_tasks": successful_tasks,
            "failed_tasks": failed_tasks,
            "total_tasks": total_tasks,
        }

        # Append per-level accuracies: accuracy_easy, accuracy_medium, …
        for level, count in level_correct_count.items():
            level_total = count["total"]
            metrics[f"accuracy_{level}"] = count["success"] / level_total if level_total > 0 else 0.0
            metrics[f"total_{level}"] = level_total

        return metrics


