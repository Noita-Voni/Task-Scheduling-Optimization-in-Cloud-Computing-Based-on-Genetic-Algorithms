"""Fixed Example 1 inputs from Hamed & Alkinani (2021), Tables 1–3.

This module defines and validates problem data only. It performs no scheduling.
"""

from collections import deque


# Row labels for Table 2 and endpoint labels for Table 1.
TASK_IDS = ("t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8", "t9", "t10")

# Column labels for Table 2 and keys for the rates in Table 3.
PROCESSOR_IDS = ("P1", "P2", "P3", "P4")

# Table 2, printed page 3296: rows follow TASK_IDS; columns follow PROCESSOR_IDS.
# These are computation durations, not monetary charges.
COMPUTATION_DURATIONS = (
    (4, 4, 4, 3),  # t1
    (3, 5, 5, 4),  # t2
    (4, 2, 5, 5),  # t3
    (2, 1, 4, 4),  # t4
    (5, 3, 5, 4),  # t5
    (5, 1, 3, 1),  # t6
    (1, 2, 5, 4),  # t7
    (1, 1, 4, 3),  # t8
    (4, 1, 3, 5),  # t9
    (3, 2, 4, 4),  # t10
)

# Table 3, printed page 3297: unspecified monetary units per second.
PROCESSOR_RATES = {"P1": 1, "P2": 7, "P3": 2, "P4": 2}

# Table 1, printed page 3296: (parent, child, communication delay).
# The approved interpretation reads each positive cell as column -> row.
# Keep dependencies explicit; zero effective communication later will not remove them.
COMMUNICATION_EDGES = (
    ("t1", "t2", 18),
    ("t1", "t3", 3),
    ("t2", "t4", 16),
    ("t3", "t4", 14),
    ("t3", "t5", 12),
    ("t4", "t6", 8),
    ("t5", "t7", 1),
    ("t6", "t8", 12),
    ("t7", "t8", 10),
    ("t7", "t9", 9),
    ("t8", "t10", 7),
    ("t9", "t10", 16),
)


def validate_problem(
    task_ids=TASK_IDS,
    processor_ids=PROCESSOR_IDS,
    computation_durations=COMPUTATION_DURATIONS,
    processor_rates=PROCESSOR_RATES,
    communication_edges=COMMUNICATION_EDGES,
):
    """Check this 10-task/4-processor instance without changing the input data.

    Return a validation summary, or raise ValueError describing the first failure.
    Optional inputs allow the same validation to check a loaded copy of the instance.
    """
    if len(task_ids) != 10 or len(set(task_ids)) != 10:
        raise ValueError("Expected 10 unique task IDs.")
    if set(task_ids) != set(TASK_IDS):
        raise ValueError("Task IDs must be t1 through t10.")

    if len(processor_ids) != 4 or len(set(processor_ids)) != 4:
        raise ValueError("Expected 4 unique processor IDs.")
    if set(processor_ids) != set(PROCESSOR_IDS):
        raise ValueError("Processor IDs must be P1 through P4.")

    if len(computation_durations) != 10:
        raise ValueError("The duration matrix must have 10 task rows.")
    for task, row in zip(task_ids, computation_durations):
        if len(row) != 4:
            raise ValueError(f"Duration row for {task} must have 4 processor values.")
        if any(type(value) is not int or value <= 0 for value in row):
            raise ValueError(f"Durations for {task} must be positive integers.")

    if len(processor_rates) != 4 or set(processor_rates) != set(processor_ids):
        raise ValueError("Expected one processor rate for each of P1 through P4.")
    if any(type(rate) is not int or rate <= 0 for rate in processor_rates.values()):
        raise ValueError("Processor rates must be positive integers.")

    if len(communication_edges) != 12:
        raise ValueError("Expected 12 directed communication edges.")

    successors = {task: [] for task in task_ids}
    incoming_count = {task: 0 for task in task_ids}
    edge_pairs = set()
    for edge in communication_edges:
        if len(edge) != 3:
            raise ValueError("Each edge must contain a parent, child and delay.")
        parent, child, delay = edge
        if parent not in successors or child not in successors:
            raise ValueError(f"Unknown task endpoint in edge {parent} -> {child}.")
        if parent == child:
            raise ValueError(f"Self-loop at {parent} is not allowed.")
        if (parent, child) in edge_pairs:
            raise ValueError(f"Duplicate directed edge {parent} -> {child}.")
        if type(delay) is not int or delay < 0:
            raise ValueError("Communication delays must be non-negative integers.")
        edge_pairs.add((parent, child))
        successors[parent].append(child)
        incoming_count[child] += 1

    sources = tuple(task for task in task_ids if incoming_count[task] == 0)
    sinks = tuple(task for task in task_ids if not successors[task])

    # Kahn's cycle check operates on local copies; it does not generate a chromosome.
    remaining_incoming = incoming_count.copy()
    ready = deque(sources)
    visited_count = 0
    while ready:
        task = ready.popleft()
        visited_count += 1
        for child in successors[task]:
            remaining_incoming[child] -= 1
            if remaining_incoming[child] == 0:
                ready.append(child)
    if visited_count != len(task_ids):
        raise ValueError("The dependency graph contains a directed cycle.")

    if sources != ("t1",):
        raise ValueError(f"Expected t1 as the sole source; found {sources}.")
    if sinks != ("t10",):
        raise ValueError(f"Expected t10 as the sole sink; found {sinks}.")

    return {
        "task_count": len(task_ids),
        "processor_count": len(processor_ids),
        "unique_task_ids": True,
        "unique_processor_ids": True,
        "duration_matrix_shape": (len(computation_durations), len(processor_ids)),
        "positive_duration_count": sum(len(row) for row in computation_durations),
        "processor_rate_count": len(processor_rates),
        "positive_processor_rates": True,
        "edge_count": len(communication_edges),
        "unique_directed_edge_count": len(edge_pairs),
        "valid_edge_endpoints": True,
        "no_self_loops": True,
        "non_negative_communication_delays": True,
        "acyclic": True,
        "sources": sources,
        "sinks": sinks,
    }


if __name__ == "__main__":
    summary = validate_problem()
    print("Phase 4.1 problem validation: PASS")
    for name, value in summary.items():
        print(f"{name}: {value}")
