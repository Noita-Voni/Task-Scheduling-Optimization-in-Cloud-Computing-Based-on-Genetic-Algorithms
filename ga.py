"""Complete makespan-minimising GA for one run on the published instance.

The caller owns the RNG. This module performs no research experiment, baseline
comparison, plotting or export; run_ga returns the run's results in memory.
"""

from chromosome import generate_random_chromosome, validate_chromosome
from operators import (
    TOURNAMENT_SIZE,
    identify_elite,
    mutate_processor,
    tournament_selection,
    whole_portion_crossover,
)
from scheduler import schedule


DEFAULT_CONFIGURATION = {
    "population_size": 20,
    "generations": 100,
    "tournament_size": TOURNAMENT_SIZE,
    "crossover_probability": 0.95,
    "mutation_probability": 0.02,
    "elitism": 1,
    "fitness": "makespan",
}


def _check_configuration(configuration):
    if type(configuration["population_size"]) is not int or configuration["population_size"] < TOURNAMENT_SIZE:
        raise ValueError("Population size must be an integer of at least 3.")
    if type(configuration["generations"]) is not int or configuration["generations"] < 0:
        raise ValueError("Generations must be a non-negative integer.")
    if type(configuration["tournament_size"]) is not int or configuration["tournament_size"] != TOURNAMENT_SIZE:
        raise ValueError("The approved tournament size is 3.")
    if type(configuration["elitism"]) is not int or configuration["elitism"] != 1:
        raise ValueError("The approved replacement rule retains exactly 1 elite.")
    if configuration["fitness"] != "makespan":
        raise ValueError("The only supported fitness is makespan, which is minimised.")
    for name in ("crossover_probability", "mutation_probability"):
        probability = configuration[name]
        if (
            isinstance(probability, bool) or not isinstance(probability, (int, float))
            or not 0 <= probability <= 1
        ):
            raise ValueError(f"{name} must be a number between 0 and 1 inclusive.")


def _generation_record(generation, fitness_values, evaluation_count):
    return {
        "generation": generation,
        "best_makespan": min(fitness_values),
        "mean_makespan": sum(fitness_values) / len(fitness_values),
        "population_size": len(fitness_values),
        "evaluation_count": evaluation_count,
    }


def run_ga(rng, configuration=None):
    """Run the GA with a caller-owned RNG and explicit configuration overrides.

    Defaults are the frozen 20-individual, 100-generation protocol. Generation
    zero is the evaluated initial population. Each replacement retains one
    unchanged first-minimum elite and evaluates population_size - 1 children.
    There is no early stopping or duplicate removal. Every child is scheduled,
    even if its chromosome has previously appeared.

    Current schedule results are retained so the copied elite and final winner
    do not need reevaluation. History includes generation zero. The supplied
    configuration and published problem data are not modified.
    """
    config = DEFAULT_CONFIGURATION.copy()
    if configuration is not None:
        if not isinstance(configuration, dict):
            raise ValueError("Configuration must be a dictionary of named settings.")
        unknown = set(configuration) - set(DEFAULT_CONFIGURATION)
        if unknown:
            raise ValueError(f"Unknown configuration settings: {unknown}.")
        config.update(configuration)
    _check_configuration(config)

    population = [generate_random_chromosome(rng) for _ in range(config["population_size"])]
    schedule_results = [schedule(chromosome) for chromosome in population]
    fitness_values = [result["metrics"]["makespan"] for result in schedule_results]
    evaluation_count = len(schedule_results)
    initial_population = tuple(population)
    initial_fitness = tuple(fitness_values)
    history = [_generation_record(0, fitness_values, evaluation_count)]

    for generation in range(1, config["generations"] + 1):
        elite = identify_elite(population, fitness_values)
        elite_index = population.index(elite)
        next_population = [(tuple(elite[0]), tuple(elite[1]))]
        next_schedule_results = [schedule_results[elite_index]]
        next_fitness = [fitness_values[elite_index]]

        for _ in range(config["population_size"] - config["elitism"]):
            parent_a = tournament_selection(population, fitness_values, rng)
            parent_b = tournament_selection(population, fitness_values, rng)
            child = whole_portion_crossover(parent_a, parent_b, config["crossover_probability"], rng)
            child = mutate_processor(child, config["mutation_probability"], rng)
            validate_chromosome(child)
            child_schedule = schedule(child)
            evaluation_count += 1
            next_population.append(child)
            next_schedule_results.append(child_schedule)
            next_fitness.append(child_schedule["metrics"]["makespan"])

        population = next_population
        schedule_results = next_schedule_results
        fitness_values = next_fitness
        history.append(_generation_record(generation, fitness_values, evaluation_count))

    best_chromosome = identify_elite(population, fitness_values)
    best_index = population.index(best_chromosome)
    best_schedule = schedule_results[best_index]
    best_metrics = best_schedule["metrics"]
    return {
        "configuration": config,
        "initial_population": initial_population,
        "initial_fitness": initial_fitness,
        "final_population": tuple(population),
        "final_fitness": tuple(fitness_values),
        "best_chromosome": best_chromosome,
        "best_schedule": best_schedule,
        "best_makespan": best_metrics["makespan"],
        "execution_cost": best_metrics["execution_cost"],
        "paper_aggregate_utilisation_pct": best_metrics["paper_aggregate_utilisation_pct"],
        "mean_processor_utilisation_pct": best_metrics["mean_processor_utilisation_pct"],
        "history": history,
        "evaluation_count": evaluation_count,
    }
