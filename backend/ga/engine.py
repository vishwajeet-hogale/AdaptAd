"""
Genetic algorithm engine.

Handles population initialization, selection, crossover, mutation,
elite preservation, and convergence detection.
"""

import random
from typing import Optional

import numpy as np

from ..state import Chromosome, UserProfile, AdCandidate, ContentItem
from ..config import config, GAConfig
from .fitness import evaluate_population_fitness


def init_population(
    size: int, seed: Optional[int] = None
) -> list[Chromosome]:
    """
    Initialize a random population of chromosomes.

    Each gene is sampled uniformly from [0, 1].
    """
    rng = random.Random(seed)
    population = []
    for _ in range(size):
        vec = [round(rng.random(), 4) for _ in range(8)]
        population.append(Chromosome.from_vector(vec))
    return population


def select_parents(
    population: list[Chromosome],
    fitnesses: list[float],
    num_parents: int,
    rng: random.Random,
) -> list[Chromosome]:
    """
    Tournament selection.

    Pick `num_parents` chromosomes. Each is chosen via a 3-way tournament:
    sample 3 at random and keep the best.
    """
    parents = []
    for _ in range(num_parents):
        candidates = rng.sample(list(range(len(population))), k=min(3, len(population)))
        best_idx = max(candidates, key=lambda i: fitnesses[i])
        parents.append(population[best_idx])
    return parents


def uniform_crossover(
    parent_a: Chromosome,
    parent_b: Chromosome,
    rng: random.Random,
) -> tuple[Chromosome, Chromosome]:
    """
    Uniform crossover: each gene is taken from parent A or B with equal probability.

    Returns two offspring.
    """
    vec_a = parent_a.to_vector()
    vec_b = parent_b.to_vector()
    child_a = []
    child_b = []
    for i in range(len(vec_a)):
        if rng.random() < 0.5:
            child_a.append(vec_a[i])
            child_b.append(vec_b[i])
        else:
            child_a.append(vec_b[i])
            child_b.append(vec_a[i])
    return Chromosome.from_vector(child_a), Chromosome.from_vector(child_b)


def mutate(
    chromosome: Chromosome,
    mutation_rate: float,
    mutation_strength: float,
    rng: random.Random,
) -> Chromosome:
    """
    Per-gene Gaussian mutation.

    Each gene has `mutation_rate` probability of being mutated.
    Mutation delta is sampled from N(0, mutation_strength/2) and clamped.
    """
    vec = chromosome.to_vector()
    mutated = []
    for gene in vec:
        if rng.random() < mutation_rate:
            delta = rng.gauss(0, mutation_strength / 2)
            gene = max(0.0, min(1.0, round(gene + delta, 4)))
        mutated.append(gene)
    return Chromosome.from_vector(mutated)


def compute_diversity(population: list[Chromosome]) -> float:
    """
    Compute population diversity as mean pairwise L2 distance, normalized to [0,1].

    Higher diversity means the population is more spread out in gene space.
    """
    if len(population) < 2:
        return 0.0
    vecs = np.array([c.to_vector() for c in population])
    # Mean variance across all genes.
    variance = float(np.mean(np.var(vecs, axis=0)))
    # Max possible variance for uniform [0,1] is 1/12 per gene.
    max_variance = 1.0 / 12.0
    return min(1.0, variance / max_variance)


def evolve_one_generation(
    population: list[Chromosome],
    fitnesses: list[float],
    ga_cfg: GAConfig,
    rng: random.Random,
) -> list[Chromosome]:
    """
    Produce the next generation from the current population and fitnesses.

    Steps:
    1. Sort by fitness descending.
    2. Preserve top elite_ratio as elites (unchanged).
    3. Fill remainder with offspring from tournament selection + crossover + mutation.
    4. If stuck for 20 generations (handled by caller), restart is triggered externally.
    """
    pop_size = len(population)
    elite_count = max(1, int(pop_size * ga_cfg.elite_ratio))

    # Sort by fitness descending.
    ranked = sorted(zip(fitnesses, population), key=lambda x: x[0], reverse=True)
    sorted_pop = [chrom for _, chrom in ranked]
    sorted_fits = [f for f, _ in ranked]

    elites = sorted_pop[:elite_count]
    offspring: list[Chromosome] = []

    while len(offspring) < pop_size - elite_count:
        parents = select_parents(sorted_pop, sorted_fits, 2, rng)
        child_a, child_b = uniform_crossover(parents[0], parents[1], rng)
        child_a = mutate(child_a, ga_cfg.mutation_rate, ga_cfg.mutation_strength, rng)
        child_b = mutate(child_b, ga_cfg.mutation_rate, ga_cfg.mutation_strength, rng)
        offspring.append(child_a)
        if len(offspring) < pop_size - elite_count:
            offspring.append(child_b)

    return elites + offspring


def check_convergence(
    fitness_history: list[float],
    window: int,
    threshold: float,
) -> bool:
    """
    Return True if the best fitness has improved by less than `threshold`
    over the last `window` generations.
    """
    if len(fitness_history) < window:
        return False
    recent = fitness_history[-window:]
    improvement = max(recent) - min(recent)
    return improvement < threshold


class GAEngine:
    """
    Stateful GA engine.

    Usage:
        engine = GAEngine(users, content, ads)
        for generation_result in engine.run():
            print(generation_result)
        best = engine.best_chromosome
    """

    def __init__(
        self,
        users: list[UserProfile],
        content_items: list[ContentItem],
        ad_pool: list[AdCandidate],
        ga_cfg: Optional[GAConfig] = None,
        seed: Optional[int] = 42,
    ):
        self.users = users
        self.content_items = content_items
        self.ad_pool = ad_pool
        self.cfg = ga_cfg or config.ga
        self.rng = random.Random(seed)
        self.np_seed = seed or 0

        self.population: list[Chromosome] = []
        self.fitnesses: list[float] = []
        self.fitness_history: list[float] = []
        self.current_generation: int = 0
        self.best_chromosome: Optional[Chromosome] = None
        self.best_fitness: float = 0.0
        self.converged: bool = False
        self.generations_since_improvement: int = 0

    def initialize(self) -> None:
        """Initialize random population and evaluate initial fitnesses."""
        self.population = init_population(
            self.cfg.population_size, seed=self.rng.randint(0, 2**31)
        )
        self._evaluate()

    def _evaluate(self) -> None:
        """Evaluate fitness for the current population."""
        self.fitnesses = evaluate_population_fitness(
            self.population,
            self.users,
            self.content_items,
            self.ad_pool,
            scenarios_per_user=10,
            rng_seed=self.np_seed + self.current_generation,
        )
        best_idx = int(np.argmax(self.fitnesses))
        gen_best = self.fitnesses[best_idx]

        if gen_best > self.best_fitness:
            self.best_fitness = gen_best
            best_chrom = self.population[best_idx].model_copy()
            best_chrom.fitness = gen_best
            self.best_chromosome = best_chrom
            self.generations_since_improvement = 0
        else:
            self.generations_since_improvement += 1

        self.fitness_history.append(gen_best)

    def _restart(self) -> None:
        """Force restart with fresh random population when stuck."""
        print(
            f"Warning: GA stuck for {self.cfg.stuck_restart_threshold} generations. "
            "Restarting with fresh random population."
        )
        self.population = init_population(
            self.cfg.population_size, seed=self.rng.randint(0, 2**31)
        )
        self.generations_since_improvement = 0
        self._evaluate()

    def step(self) -> dict:
        """
        Run one generation. Returns a dict with generation stats.

        Call initialize() before the first step().
        """
        if not self.population:
            raise RuntimeError("Call initialize() before step().")

        # Check for stuck condition before evolving.
        if self.generations_since_improvement >= self.cfg.stuck_restart_threshold:
            self._restart()

        self.population = evolve_one_generation(
            self.population, self.fitnesses, self.cfg, self.rng
        )
        self.current_generation += 1
        self._evaluate()

        avg_fitness = float(np.mean(self.fitnesses))
        diversity = compute_diversity(self.population)

        self.converged = check_convergence(
            self.fitness_history,
            self.cfg.convergence_window,
            self.cfg.convergence_threshold,
        )

        return {
            "generation": self.current_generation,
            "best_fitness": round(self.best_fitness, 6),
            "avg_fitness": round(avg_fitness, 6),
            "diversity": round(diversity, 4),
            "converged": self.converged,
            "best_chromosome": self.best_chromosome.to_vector() if self.best_chromosome else None,
        }

    def run(self, max_generations: Optional[int] = None):
        """
        Generator that runs the GA until convergence or max_generations.

        Yields a stats dict after each generation.
        """
        if not self.population:
            self.initialize()

        limit = max_generations or self.cfg.max_generations
        while self.current_generation < limit and not self.converged:
            stats = self.step()
            yield stats
            if self.converged:
                break

    def get_best_chromosome(self) -> Optional[Chromosome]:
        return self.best_chromosome

    def get_population_stats(self) -> dict:
        if not self.fitnesses:
            return {}
        return {
            "generation": self.current_generation,
            "population_size": len(self.population),
            "best_fitness": round(self.best_fitness, 6),
            "avg_fitness": round(float(np.mean(self.fitnesses)), 6),
            "min_fitness": round(float(np.min(self.fitnesses)), 6),
            "diversity": round(compute_diversity(self.population), 4),
            "converged": self.converged,
            "generations_since_improvement": self.generations_since_improvement,
        }
