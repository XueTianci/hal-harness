# Disclaimer: this is not a functional agent and is only for demonstration purposes. This implementation is just a single model call.

def run(input: dict[str, dict], **kwargs) -> dict[str, str]:

    assert 'model_name' in kwargs, 'model_name is required'
    assert len(input) == 1, 'input must contain only one task'

    task_id, task = list(input.items())[0]
    print(f"Task ID: {task_id}")
    print(f"Task: {task}")
    
    # run your agent here to collect trajectories

    # return the results paths
    results = {}
    results[task_id] = {"trajectory": f"./results/online_mind2web/RUN_ID/{task_id}/result/trajectory", 
                        "result_file": f"./results/online_mind2web/RUN_ID/{task_id}/result/result.json"}
    
        
    return results