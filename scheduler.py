"""Deterministic, append-only scheduling for the published problem instance."""

from problem import (
    COMMUNICATION_EDGES,
    COMPUTATION_DURATIONS,
    PROCESSOR_IDS,
    PROCESSOR_RATES,
    TASK_IDS,
    validate_problem,
)


def schedule(chromosome):
    """Evaluate one supplied positional chromosome (D, O).

    Task O[k] is assigned to processor D[k]. O must contain every published
    task exactly once and respect precedence. Invalid input raises ValueError.
    The result contains task assignments, a construction-order trace and metrics.
    Neither the chromosome nor the published problem data is modified.
    """
    validate_problem()
    if not isinstance(chromosome, (tuple, list)) or len(chromosome) != 2:
        raise ValueError("Expected a positional chromosome (D, O).")
    distribution, order = chromosome
    if not isinstance(distribution, (tuple, list)) or not isinstance(order, (tuple, list)):
        raise ValueError("D and O must be tuples or lists.")
    if len(distribution) != len(TASK_IDS) or len(order) != len(TASK_IDS):
        raise ValueError("D and O must each contain 10 entries.")
    if set(order) != set(TASK_IDS):
        raise ValueError("O must contain every published task exactly once.")
    if any(processor not in PROCESSOR_IDS for processor in distribution):
        raise ValueError("Every entry in D must be P1, P2, P3 or P4.")

    positions = {task: position for position, task in enumerate(order)}
    for parent, child, _ in COMMUNICATION_EDGES:
        if positions[parent] >= positions[child]:
            raise ValueError(f"Task order violates precedence: {parent} -> {child}.")

    assignments = dict(zip(order, distribution))
    task_rows = {task: index for index, task in enumerate(TASK_IDS)}
    processor_columns = {processor: index for index, processor in enumerate(PROCESSOR_IDS)}
    predecessors = {task: [] for task in TASK_IDS}
    for parent, child, delay in COMMUNICATION_EDGES:
        predecessors[child].append((parent, delay))

    processor_ready = {processor: 0 for processor in PROCESSOR_IDS}
    finish_times = {}
    trace = []
    for task in order:
        processor = assignments[task]
        arrivals = []
        for parent, published_delay in predecessors[task]:
            parent_processor = assignments[parent]
            effective_delay = 0 if parent_processor == processor else published_delay
            parent_finish = finish_times[parent]
            arrivals.append({
                "task": parent,
                "processor": parent_processor,
                "finish": parent_finish,
                "published_communication_delay": published_delay,
                "effective_communication_delay": effective_delay,
                "arrival": parent_finish + effective_delay,
            })

        data_ready = max((parent["arrival"] for parent in arrivals), default=0)
        ready_before = processor_ready[processor]
        start = max(data_ready, ready_before)
        duration = COMPUTATION_DURATIONS[task_rows[task]][processor_columns[processor]]
        finish = start + duration
        rate = PROCESSOR_RATES[processor]
        trace.append({
            "task": task,
            "processor": processor,
            "predecessors": arrivals,
            "data_ready": data_ready,
            "processor_ready": ready_before,
            "start": start,
            "finish": finish,
            "duration": duration,
            "processor_rate": rate,
            "execution_charge": duration * rate,
        })
        finish_times[task] = finish
        processor_ready[processor] = finish

    return {
        "task_assignments": assignments,
        "trace": trace,
        "metrics": calculate_metrics(trace),
    }


def calculate_metrics(trace):
    """Aggregate a completed schedule trace, keeping both utilisation definitions.

    Execution cost covers assigned processing time only. Utilisation is reported
    as a percentage and is not used to select or optimise any schedule.
    """
    if not trace:
        raise ValueError("Cannot calculate metrics for an empty schedule trace.")

    makespan = max(row["finish"] for row in trace)
    busy_times = {processor: 0 for processor in PROCESSOR_IDS}
    for row in trace:
        busy_times[row["processor"]] += row["duration"]
    total_busy = sum(busy_times.values())
    execution_cost = sum(row["execution_charge"] for row in trace)

    return {
        "makespan": makespan,
        "processor_busy_times": busy_times,
        "execution_cost": execution_cost,
        "paper_aggregate_utilisation_pct": 100 * total_busy / makespan,
        "mean_processor_utilisation_pct": 100 * total_busy / (len(PROCESSOR_IDS) * makespan),
    }
