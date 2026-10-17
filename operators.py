"""Independent GA operators for the approved positional chromosome design.

Lower makespan is always better. Stochastic operators receive a caller-owned
RNG, and none evaluates schedules or modifies the supplied chromosomes.
"""

from math import isfinite

from chromosome import validate_chromosome
from problem import PROCESSOR_IDS


TOURNAMENT_SIZE = 3


def _check_population_fitness(population, fitness_values):
    if not population:
        raise ValueError("The population must not be empty.")
    if len(population) != len(fitness_values):
        raise ValueError("Provide one makespan fitness value per chromosome.")
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float))
        or not isfinite(value) or value <= 0
        for value in fitness_values
    ):
        raise ValueError("Makespan fitness values must be finite positive numbers.")


def _check_probability(probability):
    if (
        isinstance(probability, bool) or not isinstance(probability, (int, float))
        or not 0 <= probability <= 1
    ):
        raise ValueError("Probability must be a number between 0 and 1 inclusive.")


def tournament_selection(population, fitness_values, rng):
    """Return the best of three distinct randomly drawn population indices.

    Equal minima are resolved by the first drawn candidate. Separate calls may
    return the same individual. The supplied fitness values are used directly.
    """
    _check_population_fitness(population, fitness_values)
    if len(population) < TOURNAMENT_SIZE:
        raise ValueError("Tournament selection requires at least 3 chromosomes.")
    indices = rng.sample(range(len(population)), TOURNAMENT_SIZE)
    winner = min(indices, key=lambda index: fitness_values[index])
    return population[winner]


def whole_portion_crossover(parent_a, parent_b, crossover_probability, rng):
    """Return (D_A, O_B) on crossover, otherwise (D_A, O_A).

    Test the supplied probability once, consuming one rng.random() draw even
    at probability 0 or 1. The resulting portions are immutable tuples.
    """
    validate_chromosome(parent_a)
    validate_chromosome(parent_b)
    _check_probability(crossover_probability)
    distribution = tuple(parent_a[0])
    order = tuple(parent_b[1] if rng.random() < crossover_probability else parent_a[1])
    child = (distribution, order)
    validate_chromosome(child)
    return child


def mutate_processor(chromosome, mutation_probability, rng):
    """Test mutation once per child and, if triggered, change one D position.

    The position is uniform, as is the replacement among the other three
    processors. O remains unchanged. One probability draw is consumed even at
    probability 0 or 1; position and processor draws occur only on mutation.
    """
    validate_chromosome(chromosome)
    _check_probability(mutation_probability)
    distribution = list(chromosome[0])
    order = tuple(chromosome[1])
    if rng.random() < mutation_probability:
        position = rng.randrange(len(distribution))
        current_processor = distribution[position]
        alternatives = tuple(processor for processor in PROCESSOR_IDS if processor != current_processor)
        distribution[position] = rng.choice(alternatives)
    child = (tuple(distribution), order)
    validate_chromosome(child)
    return child


def identify_elite(population, fitness_values):
    """Return the first chromosome with minimum makespan in population order.

    This helper identifies the elite only; it does not build a next generation.
    """
    _check_population_fitness(population, fitness_values)
    winner = min(range(len(population)), key=lambda index: fitness_values[index])
    return population[winner]
