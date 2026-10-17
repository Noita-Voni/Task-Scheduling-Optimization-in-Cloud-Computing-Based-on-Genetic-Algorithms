"""Positional chromosomes for the fixed published 10-task problem.

A chromosome is (D, O): task O[k] is assigned to processor D[k]. All random
functions receive a caller-owned RNG; this module creates or seeds no RNG.
"""

from problem import COMMUNICATION_EDGES, PROCESSOR_IDS, TASK_IDS, validate_problem


def random_topological_order(rng):
    """Choose uniformly among ready tasks at each step using the supplied RNG.

    Ready tasks follow TASK_IDS (t1, t2, ..., t10) before each random choice.
    This generates valid orders directly, but is not necessarily uniform over
    the set of all valid topological orders.
    """
    validate_problem()
    predecessors = {task: set() for task in TASK_IDS}
    for parent, child, _ in COMMUNICATION_EDGES:
        predecessors[child].add(parent)

    order = []
    scheduled = set()
    for _ in TASK_IDS:
        ready = [
            task for task in TASK_IDS
            if task not in scheduled and predecessors[task].issubset(scheduled)
        ]
        if not ready:
            raise ValueError("No ready task exists; a valid task order cannot be generated.")
        task = rng.choice(ready)
        order.append(task)
        scheduled.add(task)
    return tuple(order)


def random_processor_distribution(rng):
    """Sample one of the four processors equally for each chromosome position.

    Draws are independent of the task order; the function does not inspect O.
    """
    return tuple(rng.choice(PROCESSOR_IDS) for _ in TASK_IDS)


def generate_random_chromosome(rng):
    """Return a valid (D, O), drawing D first and then O from the supplied RNG."""
    distribution = random_processor_distribution(rng)
    order = random_topological_order(rng)
    chromosome = (distribution, order)
    validate_chromosome(chromosome)
    return chromosome


def validate_chromosome(chromosome):
    """Return True for a valid supplied chromosome; otherwise raise ValueError.

    Validation checks structure, IDs and precedence only. It does not calculate
    timing, execution cost, utilisation or fitness, and does not change inputs.
    """
    if not isinstance(chromosome, (tuple, list)) or len(chromosome) != 2:
        raise ValueError("Expected a positional chromosome with exactly two portions (D, O).")
    distribution, order = chromosome
    if not isinstance(distribution, (tuple, list)) or not isinstance(order, (tuple, list)):
        raise ValueError("D and O must be tuples or lists.")
    if len(distribution) != len(TASK_IDS) or len(order) != len(TASK_IDS):
        raise ValueError("D and O must each contain exactly 10 entries.")
    if any(task not in TASK_IDS for task in order):
        raise ValueError("O contains an unknown task ID; only t1 through t10 are valid.")
    if len(set(order)) != len(TASK_IDS):
        raise ValueError("O must contain every task exactly once; duplicate or missing task IDs.")
    if any(processor not in PROCESSOR_IDS for processor in distribution):
        raise ValueError("Every entry in D must be P1, P2, P3 or P4.")

    positions = {task: position for position, task in enumerate(order)}
    for parent, child, _ in COMMUNICATION_EDGES:
        if positions[parent] >= positions[child]:
            raise ValueError(f"Task order violates precedence: {parent} -> {child}.")
    return True
