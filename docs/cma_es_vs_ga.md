# CMA-ES vs Standard Genetic Algorithm for AdaptAd
## With a deep dive into Adaptive Mutation Strength

**Course:** CS6170 AI Capstone, Northeastern University
**Authors:** Craig Roberts, Arzoo Jiwani, Vishwajeet Hogale

---

## What is CMA-ES?

CMA-ES (Covariance Matrix Adaptation Evolution Strategy) is an evolutionary
algorithm specifically designed for continuous parameter optimisation. Unlike a
standard GA that mutates each gene independently with a fixed step size, CMA-ES
treats the entire chromosome as a point in an N-dimensional space and learns
**which directions in that space lead to fitness improvements**.

It does this by maintaining a **covariance matrix** — a statistical model of the
successful mutation directions found so far. Each generation the matrix is updated
based on which offspring were best, so the algorithm progressively learns to search
along the "grain" of the fitness landscape rather than against it.

In AdaptAd terms: if increasing `fatigue_weight` and `frequency_threshold` together
tends to improve fitness, CMA-ES will learn to mutate those two genes in a correlated
direction. A standard GA never discovers that relationship.

---

## Pros of CMA-ES for AdaptAd

### 1. Handles correlated genes naturally
Our 8 genes are not independent. Raising `frequency_threshold` (stricter show gate)
while leaving `fatigue_weight` low produces an inconsistent policy — the gate is
strict but the scoring ignores fatigue. CMA-ES discovers and exploits these
correlations; a standard GA must stumble onto them by chance.

### 2. Self-adapting step size
CMA-ES automatically adjusts how large its mutations are based on feedback.
Early in the run it takes large exploratory steps. As it converges it shrinks the
step size to refine the solution. Our current GA uses a fixed `mutation_strength=0.30`
throughout all 50 generations, which is simultaneously too large for fine-tuning and
can overshoot good solutions late in the run.

### 3. Better performance in higher dimensions
The standard rule of thumb is that a GA needs a population of ~10× the number of
genes to search effectively. For 8 genes our population of 30 is already slightly
underpowered; for 16 genes we would need 160. CMA-ES typically converges with a
population of `4 + floor(3 × ln(N))` — for 16 genes that is only ~11 individuals.
It achieves more with fewer fitness evaluations.

### 4. No manual crossover design
Our current GA uses one-point crossover, which can disrupt good gene combinations
(the "schema disruption" problem). CMA-ES has no crossover — it samples new
candidates from a multivariate Gaussian, preserving gene relationships automatically.

### 5. Proven benchmark performance
CMA-ES consistently ranks at or near the top on continuous black-box optimisation
benchmarks (BBOB). For a low-noise continuous fitness function like ours —
`0.6 × mean(satisfaction) + 0.4 × mean(revenue)` — it is the de facto standard.

### 6. Drop-in replacement
The `cma` Python package works with any callable fitness function. Switching
AdaptAd's `GAEngine` to CMA-ES would require approximately 30 lines of code while
keeping the chromosome, fitness function, and all agents completely unchanged.

```python
import cma

def _neg_fitness(genes: list[float]) -> float:
    # CMA-ES minimises, so negate our fitness
    chrom = Chromosome.from_vector(genes)
    return -evaluate_chromosome_fitness(chrom, users, content, ads)

es = cma.CMAEvolutionStrategy(
    x0=[0.5] * 8,       # initial guess
    sigma0=0.3,          # initial step size
    inopts={
        'maxiter': 200,
        'popsize': 12,
        'tolx': 1e-5,
        'tolfun': 1e-4,
        'bounds': [0.0, 1.0],
    }
)
es.optimize(_neg_fitness)
best_genes = es.result.xbest
```

---

## Cons of CMA-ES for AdaptAd

### 1. Loses the "genetic" narrative
Our paper frames AdaptAd around the concept of evolving a policy chromosome —
selection pressure, crossover, mutation. CMA-ES does not perform crossover or
tournament selection. Replacing the GA would require rewriting a significant portion
of the paper's methodology section.

### 2. Less interpretable internal process
A GA's generational history is intuitive: you can watch elite chromosomes survive,
offspring inherit traits, and diversity collapse over time. CMA-ES exposes a
covariance matrix that is mathematically opaque without specialist knowledge. The
live generation chart in the UI becomes harder to explain in a demo.

### 3. Memory overhead grows quadratically
The covariance matrix is N × N. For 8 genes that is a 64-element matrix —
negligible. For 50+ genes it becomes expensive. For our current 8-gene setup this
is not a practical concern.

### 4. Poor at discrete or bounded problems
CMA-ES assumes the search space is unbounded Gaussian. Our genes are hard-clipped
to [0, 1]. Applying bounds requires workarounds (clipping sampled values) that
slightly degrade the algorithm's theoretical properties. For a 0-1 bounded space
the standard GA is actually a more natural fit.

### 5. Harder to implement restart and diversity logic
Our GA has a `stuck_restart_threshold` — if the best fitness hasn't improved in 20
generations it restarts the population. CMA-ES handles stagnation internally through
step-size control, but wiring up the same restart logic and WebSocket streaming that
our UI depends on is non-trivial.

### 6. Parallel evaluation is less natural
Our GA evaluates all 30 chromosomes in a population and could trivially parallelise
across them. CMA-ES generates each generation's candidates sequentially by default,
though parallel variants exist (the `cma` package supports it via `ask/tell`).

---

## Deep dive: Adaptive Mutation Strength

### The problem with fixed mutation strength

Our current configuration:
```python
mutation_rate: float = 0.15     # 15% of genes mutated per offspring
mutation_strength: float = 0.30  # max delta per mutated gene
```

This means a mutated gene is nudged by a random value in `[-0.30, +0.30]`.
The same step size is used at **generation 1** (wide exploration needed) and
**generation 50** (fine-tuning needed). These are conflicting requirements:

- **Too large late**: overshoots good solutions. A chromosome at fitness 0.59
  gets a gene bumped by 0.28, lands at 0.51.
- **Too small early**: misses large fitness differences across the space. The
  algorithm walks slowly when it should be jumping.

### Solution 1 — Generation-based decay (simple)

Reduce mutation strength linearly or exponentially as generations increase:

```python
# Linear decay: full strength at gen 0, 10% of strength at final gen
mutation_strength = base_strength * (1 - 0.9 * (generation / max_generations))

# Exponential decay: halves every 15 generations
mutation_strength = base_strength * (0.5 ** (generation / 15))
```

This is analogous to the **temperature schedule in simulated annealing** —
aggressive early, conservative late.

### Solution 2 — 1/5 success rule (self-adaptive)

The classic rule from Evolution Strategies: after each generation, count what
fraction of mutations actually improved fitness. If more than 1/5 of mutations
improved fitness, the step size is too small (you're in a productive region —
take larger steps). If fewer than 1/5 improved, the step size is too large
(you're overshooting — shrink it).

```python
# After each generation
success_rate = num_improved_mutations / total_mutations
if success_rate > 0.20:
    mutation_strength *= 1.22   # increase step size
else:
    mutation_strength *= 0.82   # decrease step size

# Clamp to sensible bounds
mutation_strength = max(0.01, min(0.50, mutation_strength))
```

This is self-correcting and requires no manual tuning.

### Solution 3 — Per-gene adaptive strength

Different genes may need different step sizes. `frequency_threshold` controls a
linear shift over [0.35, 0.65] — small changes matter. `relevance_weight` has a
wide effect range — large changes are productive early. Each gene can track its
own step size using **individual sigma adaptation**:

```python
gene_sigmas = [0.30] * num_genes  # one step size per gene

# After evaluating offspring:
for i, gene_idx in enumerate(mutated_indices):
    if offspring_fitness > parent_fitness:
        gene_sigmas[gene_idx] *= 1.2   # this gene's direction was productive
    else:
        gene_sigmas[gene_idx] *= 0.85  # this gene's direction was not

# Apply per-gene sigma when mutating
delta = rng.gauss(0, gene_sigmas[gene_idx])
new_gene = clamp(gene + delta, 0.0, 1.0)
```

### Solution 4 — The sqrt(N) scaling rule

When adding more genes, the total mutation magnitude across the chromosome grows
with the number of genes mutated. The standard fix is to scale the per-gene step
size by `1 / sqrt(N)`:

```
mutation_strength = base_strength / sqrt(num_genes)
```

| Genes | base = 0.30 | Effective per-gene step |
|-------|-------------|------------------------|
| 8     | 0.30 / 2.83 | **0.106**              |
| 12    | 0.30 / 3.46 | **0.087**              |
| 16    | 0.30 / 4.00 | **0.075**              |

This ensures that adding genes does not inflate the total perturbation applied to
each offspring, keeping search behaviour consistent as dimensionality grows.

---

## Recommendation for AdaptAd

| Scenario | Recommendation |
|---|---|
| Stay with 8 genes, improve convergence | Add generation-based decay to `mutation_strength`. 2-line change in `ga/engine.py`. |
| Add 4–6 more genes | Add the 1/5 success rule + sqrt(N) scaling. Still a standard GA, no paper rewrite needed. |
| Push to 12+ genes for a research extension | Switch to CMA-ES via the `ask/tell` interface, keeping existing fitness function and chromosome unchanged. Describe it as "we compared GA and CMA-ES" — a comparison study strengthens the paper. |
| Maximise fitness ceiling | The ceiling is in the outcome reward table, not the chromosome. Fix the reward structure before adding genes or changing the algorithm. |

The most impactful change for H1 (fitness > 0.58) is **not more genes** —
it is ensuring the existing 8 genes have enough exploration early and enough
precision late. Generation-based mutation decay costs one line of code and is
worth implementing regardless of any other change.

---

## References

- Hansen, N. (2016). *The CMA Evolution Strategy: A Tutorial*. arXiv:1604.00772.
- Rechenberg, I. (1973). *Evolutionsstrategie*. Frommann-Holzboog.
- Back, T. (1996). *Evolutionary Algorithms in Theory and Practice*. Oxford University Press.
- Bäck, T., & Schwefel, H. P. (1993). An overview of evolutionary algorithms for parameter optimisation. *Evolutionary Computation*, 1(1), 1–23.
