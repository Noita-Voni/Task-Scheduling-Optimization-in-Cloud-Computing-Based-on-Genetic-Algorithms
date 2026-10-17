# Phase 6 — Final Analysis and Research Paper Plan

## 1. Purpose and evidence base

This document consolidates the completed reproduction of Hamed and Alkinani (2021), the implementation decisions required to make the method executable, and the results of the paired Genetic Algorithm (GA) and random-search experiments. It is intended as the analytical foundation for the final optimisation research paper.

The analysis uses only the original paper, the Phase 4.0 readiness audit, the frozen project source code and tests, and the retained Phase 4.6 and Phase 4.7 CSV outputs. No experiment was rerun and no result was generated for this phase.

The central finding is:

> Under the documented reproduction assumptions, the reproduced GA improved over its initial populations but did not consistently outperform an equal-budget random valid-search baseline on the small published 10-task instance.

This finding is specific to the reconstructed instance and protocol. It neither disproves the original paper nor establishes that GAs are generally inferior to random search.

## 2. The original study

### 2.1 Research problem and cloud-scheduling context

Hamed and Alkinani (2021) study task scheduling in a cloud-computing setting. The scheduling problem assigns dependent tasks to heterogeneous processors. A schedule must respect task precedence while accounting for processor-dependent computation durations and communication delays between dependent tasks. The paper presents a GA intended to improve completion time, execution cost, and resource utilisation.

The application is represented as a directed acyclic graph (DAG). A directed edge from a parent task to a child task means that the child cannot use the parent's output until the parent has finished. When the tasks use different processors, the edge's communication delay is added to the parent's finish time. When they use the same processor, the effective communication delay is zero. Each processor has its own ready time, and each task has a different computation duration on each processor.

### 2.2 Directly reported paper details

The following points are directly supported by the paper:

- A chromosome contains a processor-distribution portion and a task-scheduling portion.
- The two portions are paired by chromosome position: the task at position `k` is assigned to the processor at position `k`.
- Initial task orders must respect precedence, while initial processor entries are random.
- Fitness minimises completion time.
- Crossover forms a child from the complete processor portion of one parent and the complete task-order portion of another.
- Mutation changes a randomly selected processor entry.
- The reported experimental parameters include population size 20, crossover probability 0.95, and mutation probability 0.02.
- Example 1 uses 10 tasks and 4 processors. Its inputs are presented through Table 1 communication values, Table 2 computation durations, and Table 3 processor rates.
- Figure 5 presents the candidate chromosome

  ```text
  D = (P4, P1, P1, P3, P4, P1, P4, P2, P4, P2)
  O = (t1, t3, t5, t7, t2, t4, t6, t9, t8, t10)
  ```

- The paper reports completion time 46 and execution cost 64 for this example.

The paper discusses completion time, execution cost, and resource utilisation as objectives or reported outcomes. Its explicit GA fitness definition, however, minimises completion time. The present reproduction therefore uses makespan alone for selection and records cost and utilisation as descriptive metrics.

### 2.3 Findings inferred by the audit

Several details required interpretation and must not be presented as author-stated facts:

- Table 1 is interpreted with rows as child tasks and columns as parent tasks. This orientation yields 12 directed edges, a precedence-valid Figure 5 order, and the reported timing reconstruction. The table caption does not state the orientation explicitly.
- Table 4's numerical scheduling rows reproduce Figure 5 when read in Figure 5 chromosome order, but its printed task labels appear to follow `t1` through `t10`. Treating this as a task-label error is a strong audit inference, not an author-issued correction.
- The printed execution-cost equation lacks assignment indicators. Applying it literally would charge every task on every processor and would be independent of the chromosome. The reproduction uses assigned task duration multiplied by the assigned processor rate, which produces the reported cost of 64.
- The paper's utilisation calculation and reported busy times do not reconcile with the reconstructed Figure 5 schedule. The reproduction consequently reports the literal aggregate-style utilisation and a separately normalised mean processor utilisation.
- The published completion time of 46 is a candidate result, not a demonstrated global optimum. For example, assigning all tasks to P2 gives a feasible makespan of 22 under the published data, although this arithmetic witness does not establish that 22 is globally optimal.

These distinctions preserve the difference between evidence in the paper and transparent choices made during reconstruction.

## 3. What the project reproduced

The project encoded the fixed 10-task, 4-processor instance from Tables 1–3. It includes the 10 task identifiers, 4 processor identifiers, all 40 positive task-processor computation durations, 4 processor rates, and 12 directed communication edges. Validation confirms one source task (`t1`), one sink task (`t10`), valid edge endpoints, unique directed edges, and an acyclic graph.

The deterministic scheduler decodes the positional chromosome so that task `O[k]` uses processor `D[k]`. For each task it computes predecessor arrival times, zeroes communication for same-processor dependencies, takes the maximum predecessor arrival as data-ready time, and takes the maximum of data-ready and processor-ready time as task start. Finish time is start plus the Table 2 duration for the assigned processor. The assigned processor then becomes ready at that finish time.

The Figure 5 reconstruction produced:

| Metric | Reproduced value |
|---|---:|
| Makespan | 46 |
| Execution cost | 64 |
| Busy time P1 | 11 |
| Busy time P2 | 3 |
| Busy time P3 | 5 |
| Busy time P4 | 11 |
| Paper aggregate utilisation | 65.217391% |
| Mean processor utilisation | 16.304348% |

The makespan and assigned-duration cost agree with the published values. The corrected busy-time vector comes from the reconstructed trace and differs from the paper's later busy-time table.

## 4. Reproduction assumptions

The original paper does not provide source code or enough detail to recover every executable decision. The following are reproduction-design choices rather than claims about the authors' hidden implementation:

| Decision | Implemented convention | Status |
|---|---|---|
| Parent selection | Tournament selection of the best makespan among 3 distinct sampled indices | Reproduction choice |
| Parent draws | Two independent tournaments per child; both may select the same parent | Reproduction choice |
| Replacement | Generational replacement with 1 retained elite and 19 evaluated children | Reproduction choice |
| Elitism | One unchanged first-minimum elite | Reproduction choice |
| Maximum generations | 100 replacement generations after generation 0 | Reproduction choice |
| Early stopping | None | Reproduction choice because no executable optimum/stagnation criterion is supplied |
| Mutation interpretation | One probability test per child; if successful, one processor position changes to one of the other processors | Close implementation reading of an under-specified detail |
| Repeated runs | 30 complete runs | Reproduction protocol |
| Random seeds | Independent caller-owned `random.Random(seed)` instances for seeds 1–30 | Reproduction protocol |
| Fitness ties | Keep the first minimum in the relevant population or evaluation order | Reproduction choice |
| GA reporting tie | Smallest seed identifies a reported best or worst run when final makespans tie | Reporting convention |
| Random baseline | Equal-budget valid random search using the same seeds, generator, scheduler, and first 20 chromosomes | Evaluation design |
| Cost | Sum assigned duration × assigned processor rate | Approved repair of the incomplete printed equation |
| Utilisation | Report paper aggregate and mean processor utilisation separately | Approved reporting clarification |

These choices were fixed before the final comparison and were not tuned after observing results.

## 5. Final GA implementation

Each GA run begins by creating 20 valid chromosomes. For every chromosome, the processor distribution contains 10 independent draws from the four processors. The task portion is generated as a random valid topological order: at each position the generator randomly selects among tasks whose predecessors have already been scheduled. This constructs precedence-valid orders directly.

The deterministic scheduler evaluates each chromosome against the published instance. The resulting makespan is the sole fitness value. Execution cost, paper aggregate utilisation, and mean processor utilisation do not influence selection.

For each of 100 replacement generations, the algorithm retains the current first-minimum elite. It creates 19 children. Each child uses two size-3 tournaments, whole-portion crossover with probability 0.95, and processor mutation with probability 0.02. The crossover result is `(D_A, O_B)` when crossover occurs and `(D_A, O_A)` otherwise. Mutation leaves the task order unchanged. All 19 children are scheduled, including duplicates.

The evaluation accounting is therefore:

```text
20 initial evaluations + (19 children × 100 generations) = 1,920 evaluations
```

The experiment performed 30 runs using seeds 1–30 and retained all results and all 101 generation checkpoints. No result was discarded or replaced because of performance.

## 6. Equal-budget random baseline

The baseline repeatedly generates valid chromosomes with the same generator and evaluates them with the same deterministic scheduler. It keeps the first chromosome that attains the lowest makespan seen. Cost and utilisation do not affect this decision.

For each seed, random search evaluates exactly 1,920 candidates. Because it starts with the same seed and invokes the same generator before any other random draws, its first 20 chromosomes exactly match that seed's GA initial population. It then evaluates 1,900 additional independently generated valid chromosomes.

This comparison controls several major sources of difference: both methods use the same published instance, representation, schedule evaluator, validity rules, seed set, initial sample, makespan objective, and evaluation budget. The comparison isolates what the GA operators and replacement process achieve relative to continued valid random sampling under this protocol. It does not make the methods identical in runtime or in the sequence of random-number calls after the shared initial sample, and evaluation count rather than wall-clock time is the fairness criterion.

## 7. Results

### 7.1 GA outcomes

| Statistic | GA result |
|---|---:|
| Runs | 30 |
| Evaluations per run | 1,920 |
| Mean final makespan | 41.633333 |
| Median final makespan | 42 |
| Minimum final makespan | 28 |
| Maximum final makespan | 52 |
| Sample standard deviation | 5.391458 |
| Runs improving over their initial best | 29/30 |
| Final makespan below 46 | 23/30 |
| Final makespan at most 32 | 2/30 |
| Final makespan at most 22 | 0/30 |

The GA usually improved substantially over its own initial population. This shows that the evolutionary process was active under the implemented operators; it does not by itself demonstrate an advantage over another search method with the same budget.

### 7.2 Random-search outcomes

| Statistic | Random-search result |
|---|---:|
| Runs | 30 |
| Evaluations per run | 1,920 |
| Mean final makespan | 37.2 |
| Median final makespan | 38 |
| Minimum final makespan | 22 |
| Maximum final makespan | 43 |
| Sample standard deviation | 4.0633 |
| Runs improving over their initial best | 30/30 |
| Final makespan below 46 | 30/30 |
| Final makespan at most 32 | 3/30 |
| Final makespan at most 22 | 1/30 |

The strongest random run, seed 19, found the all-P2 assignment with makespan 22. Its execution cost was 154. This illustrates the conflict between makespan and cost that a makespan-only objective does not resolve.

### 7.3 Paired comparison

For each seed, the paired difference is:

```text
GA final makespan − random final makespan
```

A negative result favours the GA, zero is a tie, and a positive result favours random search.

| Paired result | Count |
|---|---:|
| GA wins | 6 |
| Ties | 0 |
| Random-search wins | 24 |
| Mean paired difference | +4.4333 |
| Median paired difference | +4 |

Random search achieved a lower final makespan on 80% of paired seeds. Its mean makespan was 4.4333 units lower, which is the same value expressed through the mean paired difference because every seed appears once in each protocol. No hypothesis test was performed, so the results should be described as observed experimental evidence rather than a formal population-level significance claim.

The reference values 46, 32, and 22 serve only as descriptive checks. The value 46 is the paper's Figure 5 candidate, while 32 and 22 are known feasible all-P1 and all-P2 schedules. None is an established global optimum threshold.

## 8. Interpretation of the main finding

The reproduced GA improved on its starting population in 29 of 30 runs, showing that its selection, crossover, mutation, and elitist replacement usually found better schedules than those in the shared initial sample. However, improvement from an initial population is a weaker test than comparison with an equal-budget search method.

Under the paired evaluation, valid random search obtained lower makespans in 24 of 30 runs and had better mean, median, minimum, maximum, and sample variability outcomes. For this instance, the implemented GA did not demonstrate a consistent advantage over spending the same number of schedule evaluations on fresh valid chromosomes.

This conclusion applies to one small 10-task instance, makespan-only fitness, the positional chromosome, the paper-style whole-portion crossover, and the documented reproduction choices. Whole-portion crossover transfers an entire processor vector and an entire valid task order. It does not construct new processor-vector combinations from the two parents; processor mutation changes at most one entry when its low-probability event occurs. These mechanics may limit exploration of processor assignments relative to 1,900 additional full random draws. This is a plausible interpretation of the observed outcome, not a separately tested causal result.

The instance itself also favours an easily sampled structural pattern: grouping dependent tasks on the same processor removes communication delays. Several published communication delays are large relative to computation durations. Random search can therefore obtain strong makespans by sampling processor distributions that consolidate tasks, even without learning from prior candidates.

The result should not be generalised to all GAs, all cloud scheduling problems, or larger DAGs. It evaluates this reproduced algorithm under this controlled protocol.

## 9. Why the reproduction can differ from the paper

Several cautious explanations are available:

1. **No original source code is available.** Equivalent prose can lead to different executable choices, especially in stochastic algorithms.
2. **No original random seed is reported.** A particular candidate cannot be expected to reappear reliably without the original random state and implementation.
3. **Selection and replacement are under-specified.** Tournament size 3, one-elite generational replacement, and first-minimum tie handling are transparent reproduction choices that may differ from the authors' program.
4. **The stopping rule is incomplete.** The paper mentions a maximum generation count or finding the best solution but does not provide the experimental maximum or an executable best-solution test. This project fixed 100 generations with no early stopping.
5. **GAs are stochastic.** A single candidate does not describe a distribution of possible outcomes. This project used 30 fixed seeds to expose that variability.
6. **The original paper does not report repeated-run statistics.** Its results cannot be compared to this 30-run distribution as though they used the same repeated-run protocol.
7. **Figure 5 is not proven globally optimal.** Feasible schedules with makespans 32 and 22 can be constructed directly from the published instance.
8. **The instance is small.** With only 10 processor positions and valid orders generated directly, 1,920 random samples can cover useful parts of the search space.
9. **Communication is relatively expensive.** Consolidating dependent tasks can remove delays that exceed several task computation durations, allowing simple assignments to perform strongly.

These points explain why results may differ without implying error or misconduct in the original work.

## 10. Limitations

- Only the published 10-task, 4-processor instance was reproduced experimentally.
- The larger examples cannot be reconstructed exactly because complete task matrices, DAGs, processor rates, and seeds are not supplied.
- Reproduction assumptions may differ from the authors' unreported implementation.
- The random baseline is simple but can be strong for a small instance with a direct valid-chromosome generator.
- Makespan alone determined fitness. Execution cost and both utilisation measures were reported rather than optimised.
- The printed cost and utilisation definitions required clarification, and some published busy-time values do not reconcile with the Figure 5 trace.
- No mutation-rate study, crossover comparison, population-size study, or multi-objective extension was performed.
- No formal optimality proof was attempted for the best observed schedule.
- No statistical hypothesis test or confidence interval was performed; the comparison remains descriptive.
- Runtime was environment-dependent and was not the equality criterion for the paired design.

## 11. Draft conclusion for the research paper

This study successfully reconstructed the published 10-task, 4-processor cloud-scheduling instance and reproduced the Figure 5 candidate's makespan of 46 and execution cost of 64 using a corrected positional chromosome interpretation. The implementation made under-specified algorithmic decisions explicit and evaluated the resulting GA over 30 fixed seeds. The GA improved on its initial population in 29 runs, but an equal-budget random valid-search baseline achieved a lower final makespan in 24 of 30 paired runs. Under this small instance, makespan-only objective, paper-style chromosome and crossover, and documented reproduction protocol, the GA therefore did not show a consistent advantage over random valid search. Future work could evaluate alternative mutation rates and crossover operators, reconstruct or publish larger complete instances, and study multi-objective fitness that explicitly balances makespan, execution cost, and utilisation.

## 12. Proposed research-paper structure

### Abstract

State the cloud task-scheduling problem, the goal of reproducing the published GA, the controlled 30-seed paired design, the main numerical results, and the bounded conclusion. Mention that random search won 24 of 30 equal-budget pairs and avoid broad claims beyond this instance.

### Introduction

Introduce dependent cloud-task scheduling, heterogeneous processors, and the tension among completion time, cost, and utilisation. Motivate computational reproduction as a way to test whether a published method can be reconstructed from available detail. End with the research question: under documented assumptions and an equal evaluation budget, how does the reproduced GA compare with valid random search on the published instance?

### Literature Study

Place the paper within work on DAG scheduling, heterogeneous computing, and evolutionary scheduling. Explain common GA components and why representation, feasibility preservation, fitness design, and baseline choice matter. Distinguish literature claims from results established by this project.

### Problem Statement

Define the 10-task, 4-processor instance, DAG edges, computation-duration matrix, processor rates, same-processor communication rule, append-only schedule construction, makespan, execution cost, and the two utilisation definitions. State that makespan is the optimisation objective.

### Methodology / Reproduction Design

Separate paper-specified details from reproduction assumptions. Present the positional chromosome, Figure 5 audit, whole-portion crossover, mutation interpretation, tournament selection, replacement, 100-generation limit, seeds 1–30, tie rules, evaluation budget, and paired baseline rationale. Explain that settings were frozen before comparison.

### Implementation

Describe the published-data module, validation, valid topological-order generator, deterministic scheduler, independent GA operators, experiment runner, random baseline, CSV retention, and permanent tests. Include the evaluation-count derivation and explain reproducibility through caller-owned seeded RNGs.

### Results

Present the Figure 5 reproduction first, followed by GA descriptive statistics, random-search descriptive statistics, reference counts, and paired differences. A compact table should compare mean, median, standard deviation, minimum, and maximum. Report all wins, ties, and losses. State that no hypothesis test was performed.

### Discussion

Interpret both parts of the evidence: the GA improved over its initial populations, while random search performed better in most equal-budget pairs. Discuss the small instance, communication-to-computation scale, same-processor delay removal, and the limited recombination performed by whole-portion crossover. Keep causal explanations tentative.

### Limitations

Cover the single small instance, unavailable larger inputs and seeds, under-specified original algorithm, descriptive-only inference, lack of an optimality certificate, makespan-only fitness, and environment-dependent runtime.

### Future Work

Propose pre-specified experiments on mutation rate, alternative crossover, population size, and larger fully published instances. Add a multi-objective study of makespan, cost, and utilisation. Future comparisons should preserve equal budgets and should add suitable inferential statistics only after the experimental design is fixed.

### Conclusion

Use the concise conclusion drafted in Section 11. Emphasise successful reconstruction, honest comparison, the local scope of the result, and the value of explicit reproducibility decisions.

### References

Include the full Hamed and Alkinani paper citation and all literature used in the final literature study. Cite software or methodological sources only when they contribute substantively to the method. The primary paper is:

Hamed, A. Y., & Alkinani, M. H. (2021). Task scheduling optimization in cloud computing based on genetic algorithms. *Computers, Materials & Continua, 69*(3), 3289–3301. https://doi.org/10.32604/cmc.2021.018658

## 13. Claims checklist for final writing

To keep the final paper accurate:

- Call 46 the paper's reported candidate makespan, not the global optimum.
- Call 32 and 22 feasible reference schedules, not proven optima.
- Attribute population 20, crossover 0.95, mutation 0.02, positional pairing, and whole-portion crossover to the paper.
- Label tournament size 3, elitism 1, 100 generations, seeds 1–30, tie rules, and the equal-budget baseline as reproduction choices.
- State that the GA used makespan only; do not imply that cost or utilisation influenced selection.
- Report that random search outperformed this reproduced GA under this protocol; do not generalise the result to GAs as a class.
- Describe paired results as descriptive because no hypothesis testing was performed.
- Keep the paper's printed metrics separate from the audit's corrected trace and clarified definitions.
