"""Equal-budget random search on the fixed published scheduling instance."""

from chromosome import generate_random_chromosome
from scheduler import schedule


INITIAL_SAMPLE_SIZE = 20
EVALUATION_BUDGET = 1920


def run_random_search(rng):
    """Evaluate 1920 generated chromosomes, retaining the first makespan minimum.

    The caller owns the RNG. The first 20 draws match a GA run with the same
    seed because both use the same generator before any GA operator draws.
    """
    initial_population = []
    initial_fitness = []
    history = []
    best_chromosome = None
    best_schedule = None
    best_makespan = None
    best_first_evaluation = None

    for evaluation_count in range(1, EVALUATION_BUDGET + 1):
        chromosome = generate_random_chromosome(rng)
        result = schedule(chromosome)
        makespan = result["metrics"]["makespan"]
        if evaluation_count <= INITIAL_SAMPLE_SIZE:
            initial_population.append(chromosome)
            initial_fitness.append(makespan)
        if best_makespan is None or makespan < best_makespan:
            best_chromosome = chromosome
            best_schedule = result
            best_makespan = makespan
            best_first_evaluation = evaluation_count
        history.append({
            "evaluation_count": evaluation_count,
            "candidate_makespan": makespan,
            "best_makespan": best_makespan,
        })

    metrics = best_schedule["metrics"]
    return {
        "initial_population": tuple(initial_population),
        "initial_fitness": tuple(initial_fitness),
        "initial_best_makespan": min(initial_fitness),
        "best_chromosome": best_chromosome,
        "best_schedule": best_schedule,
        "best_makespan": best_makespan,
        "best_first_evaluation": best_first_evaluation,
        "execution_cost": metrics["execution_cost"],
        "paper_aggregate_utilisation_pct": metrics["paper_aggregate_utilisation_pct"],
        "mean_processor_utilisation_pct": metrics["mean_processor_utilisation_pct"],
        "history": history,
        "evaluation_count": EVALUATION_BUDGET,
    }
