# Phase 4.0 — Implementation Readiness Report

**Project:** Controlled computational reproduction of Hamed & Alkinani (2021)  
**Review date:** 7 October 2026  
**Status:** Phases 4.0 and 4.1 approved by the user. The paper-based corrections, particularly positional chromosome pairing and whole-portion crossover, are adopted. Phase 4.2 is authorised for deterministic scheduling and metric calculation using the existing published inputs. The user explicitly approved assigned-duration execution cost and separate aggregate/mean utilisation reporting. The audit below records the original findings; other engineering proposals are not automatically adopted by these approvals.

**Project governance:** This report and all subsequent work are governed by the project `AGENTS.md`. Work must proceed one approved phase at a time. The frozen research design, data, GA parameters, chromosome representation, operators, baseline and evaluation protocol change only with explicit user authorisation. The user has now authorised the paper-based corrections identified here. Engineering conventions beyond those corrections remain proposals unless previously approved.

**Primary source:** Hamed, A. Y. & Alkinani, M. H. (2021). *Task Scheduling Optimization in Cloud Computing Based on Genetic Algorithms*. Computers, Materials & Continua, 69(3), 3289–3301. [Publisher record and DOI](https://www.techscience.com/cmc/v69n3/44156), [publisher PDF](https://cdn.techscience.cn/ueditor/files/cmc/TSP_CMC_69-3/TSP_CMC_18658/TSP_CMC_18658.pdf).

The review used the complete local `Research/TSP_CMC_18658.pdf`, including all 13 pages, figures, tables, algorithms, conclusion, and references. The equations and experimental tables were also inspected visually to distinguish printing problems from text-extraction errors. The publisher record confirms the paper's identity. Page references below are printed page numbers; PDF page 1 is printed page 3289.

Local source SHA-256: `FD71C0070F5D277B115F31C5A842BB86C1EA8FA118FF34BCF4ED980448AF2324`.

**Readiness finding:** The 10-task input instance is sufficiently specified for a controlled reproduction. The main scheduling formulation and your single-objective interpretation are sound. However, the chromosome's positional meaning and the crossover require correction to the handoff. Some alleged numerical inconsistencies can be reconciled: Table 4 appears to have incorrect task labels, while its numerical rows reproduce Figure 5 exactly when read in chromosome order. Completion time **46** and execution cost **64** are reproducible for that chromosome. The reported busy times and utilisation remain inconsistent, and 46 is demonstrably not the best feasible completion time for the published inputs.

## A. Paper methodology confirmed

### A1. Problem and scope

The paper models dependent tasks on heterogeneous processors. Its DAG edges express precedence and have communication delays; computation times depend on both task and assigned processor. Communication delay is zero when a parent and child share a processor. The scheduling pseudocode processes a precedence-valid list and updates each processor's ready time after placing a task. These support your basic scheduling model. [Paper, §3, pp. 3292–3293.]

The term **computation cost** means processing duration, not monetary expenditure. Equation (1) describes duration as task weight divided by processor speed, but the experiments supply randomly generated task/processor durations directly. Use Table 2 as the duration matrix. There is no need to invent task weights or processor speeds to reconstruct it.

Figure 1 is an illustrative **seven-task** graph. It is not the 10-task instance in Example 1. The latter's dependencies must be recovered from Table 1.

### A2. Explicit implementation details

| Element | What the paper specifies | Source |
|---|---|---|
| Problem structure | DAG precedence; heterogeneous processors; weighted communications | §3, pp. 3292–3293 |
| Same-processor communication | Zero delay | §3 and Eq. (2) |
| Scheduling mechanism | Process list `LT`; initialise processor ready times to zero; append work using the current ready time | Pseudocode, p. 3293 |
| Start time | Maximum of assigned processor readiness and predecessor data arrival | Pseudocode, p. 3293 |
| Finish time | Start plus the assigned task/processor duration | Eq. (4) |
| Completion time | Maximum task finish time | Eq. (3) |
| Chromosome | Processor distribution portion and task scheduling portion, paired by position | §4.1, Fig. 2 |
| Initial processor entries | Random values from 1 to N | §4.2 |
| Initial task portion | Random tasks respecting precedence | §4.2 |
| Fitness | Minimise completion time | §4.3 |
| Crossover | One child: whole distribution portion of first parent plus whole scheduling portion of second parent | §4.4.1, Fig. 3 |
| Mutation | Change one randomly selected distribution position | §4.4.2, Fig. 4 |
| Mutation target in main loop | The child | Algorithm 1, p. 3295 |
| Termination concept | A maximum generation count, or finding the best solution | §4; actual value and best-solution detection not supplied |
| Population size | 20 | §6, p. 3296 |
| Crossover probability | 0.95 | §6 |
| Mutation probability | 0.02 | §6 |
| Example 1 size | 10 tasks, 4 processors | §6.1 |
| Random input ranges | Communication 1–20; computation duration 1–5; processor rate 1–10 | §6.1, pp. 3296–3297 |
| Reported outputs | Completion time, execution cost, resource utilisation; also busy/available times, speedup and efficiency | Tables 4–8 |
| Larger example | 8 processors; Table 8 lists 20, 30, 40, 50 and 70 tasks | §6.2, Table 8 |

The population and probability values are **explicit**, not approximate. They are stated before the two examples. None of 100 generations, 30 runs, seeds 1–30, tournament size 3, or elitism 1 is reported as an experimental setting.

### A3. Chromosome meaning

Write a chromosome as two equal-length sequences:

\[
X=(D,O),\quad D=(d_1,\ldots,d_M),\quad O=(o_1,\ldots,o_M).
\]

**Task `o_k` is assigned to processor `d_k`.** The index `k` is a chromosome position, not necessarily a task ID. Both portions have M entries: there are 2M entries in the full representation.

This is supported by the explanation of Figure 2: its second processor entry P2 corresponds to the second scheduled task t4, and its fifth P2 corresponds to t6. The generic drawing's use of processor symbols such as Pn must not be mistaken for a processor portion of length N. [Paper, §4.1, p. 3294.]

Figure 5 is therefore:

| Position | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Processor D | 4 | 1 | 1 | 3 | 4 | 1 | 4 | 2 | 4 | 2 |
| Task O | 1 | 3 | 5 | 7 | 2 | 4 | 6 | 9 | 8 | 10 |

Its task-indexed assignment is consequently `(4,4,1,1,1,4,3,4,2,2)` for tasks t1 through t10. Treating D itself as that task-indexed assignment produces a different schedule.

### A4. Initialisation, crossover and mutation

The paper requires random initial allocation and random precedence-valid task ordering, but does not give a random topological-sort algorithm or sampling distribution. Your randomised topological ordering is an appropriate engineering completion of this requirement.

The specified crossover is:

\[
(D_A,O_A),(D_B,O_B)\longrightarrow(D_A,O_B).
\]

The cut is at the boundary between the two portions. It does **not** split and recombine the middle of the processor vector. Since O_B is already a valid permutation respecting precedence, this crossover preserves order validity. Because the representation is positional, inheriting a different order can also change which processor an individual task receives.

Mutation changes a single distribution entry, leaving the order unchanged. The main algorithm explicitly mutates the child, although the prose says selected parent. Using child mutation follows Algorithm 1. Whether 0.02 is tested once per child or independently at every gene is not stated precisely. A once-per-child test followed by one changed position is the closest simple reading; it remains a declared interpretation.

### A5. Fitness and scheduling equations

For a candidate X, evaluate `fitness(X) = C_max(X)` and minimise that scalar across candidates. Cost and utilisation are reported metrics. No weighted combination, Pareto ranking, or other multi-objective selection method is defined. Your single-objective interpretation is confirmed. [Paper, §4.3, p. 3294.]

Use task-indexed quantities during evaluation, after decoding the positional chromosome. Let a(i) be task i's assigned processor, Pred(i) its predecessors, w(i,p) its processing duration, and c(u,i) the stored edge delay. Then:

\[
\delta(u,i)=\begin{cases}0,&a(u)=a(i),\\c(u,i),&a(u)\ne a(i).\end{cases}
\]

\[
DR_i=\begin{cases}0,&Pred(i)=\varnothing,\\\max_{u\in Pred(i)}(FT_u+\delta(u,i)),&\text{otherwise}.\end{cases}
\]

\[
ST_i=\max(DR_i,RT_{a(i)}),\qquad FT_i=ST_i+w(i,a(i)).
\]

After scheduling i, set `RT[a(i)] = FT_i`. Initially all processor ready times are zero.

\[
C_{\max}=\max_i FT_i.
\]

These formalise your existing reasoning. The zero data-ready time for roots is an explicit boundary convention. The decoder appends tasks to processors; it does not insert later tasks into earlier idle gaps. The chromosome order governs construction and each processor's local sequence, not a global prohibition on concurrent execution.

## B. Corrections to our understanding

### B1. Corrections and their provenance

| Proposed correction | Why it matters | Basis and status |
|---|---|---|
| Make processor/task pairing positional | A task-indexed processor vector changes the meaning of published chromosomes and crossover | Paper §4.1 and Fig. 2; correction to the handoff |
| Replace the proposed internal processor-vector cut with whole-portion crossover | The paper describes this operator sufficiently clearly | Paper §4.4.1 and Fig. 3; recommended paper-based correction |
| Keep completion time as sole fitness | The prose discusses three goals, but supplies only one fitness | Paper §4.3; confirms current design |
| Restrict monetary cost to the assigned processor | Literal Eq. (5) omits assignment indicators and would charge all alternatives | Explicit mathematical repair; also supported by the reconciled cost 64 |
| Distinguish aggregate and average utilisation | Literal Eq. (6) omits division by N | Proposed reporting clarification; do not call the normalised formula the paper's exact equation |
| Treat Table 4's task names as a likely labelling error | Every numeric row agrees with Figure 5 when rows use its task order | Audit inference, not an author-issued correction |
| Treat 46 as a published candidate result, not an optimum | A valid all-P2 schedule finishes in 22 | Direct arithmetic using Table 2 |
| Evaluate GA performance without requiring a favourable result | Correct implementation does not guarantee superiority over random search | Proposed research-validity clarification |

If the simplified internal processor-vector crossover is deliberately retained, label it a methodological deviation. It is not necessary to fill an unresolved paper detail, and it should not silently replace the stated operator.

### B2. Equation issues

**Data arrival:** Eq. (2) writes the parent's finish time with the child's processor symbol. A parent must contribute its actual finish time on its own assigned processor. It also uses child/parent argument order for C. Use directed edges and explicit task IDs to remove the notation ambiguity.

**Duration:** The scheduling pseudocode mixes task indices and says task weight where Eq. (4) uses W. For heterogeneous execution, the duration must be the relevant Table 2 entry. This also reproduces Figure 5's timings.

**Execution cost:** As printed, Eq. (5) sums `W_ij × Cost(P_j)` over all task/processor pairs without an assignment indicator. Applied literally to Tables 2–3, it yields **344**, independent of the chromosome. The intended assignment-sensitive calculation is:

\[
EC=\sum_i w(i,a(i))r_{a(i)}=\sum_p B_p r_p,
\qquad B_p=\sum_{i:a(i)=p}w(i,p).
\]

Equivalently, add binary assignment indicators to the paper's double sum. The paper's cost of 64 agrees with this repaired calculation for Figure 5. There is no explicit monetary communication charge or charge for idle processor time.

**Utilisation:** The literal published equation is:

\[
U_{paper}=100\frac{\sum_pB_p}{C_{\max}}.
\]

It is a sum of processor utilisation percentages, with a possible range up to 100N percent. For a percentage of the total available processor capacity, report:

\[
U_{mean}=100\frac{\sum_pB_p}{N C_{\max}},\qquad U_p=100\frac{B_p}{C_{\max}}.
\]

**Recommendation:** retain both `paper_aggregate_utilisation_pct` and `mean_processor_utilisation_pct`, with the latter as the main interpretable metric. Include all four processors, including unused ones, in N. This recommendation changes metric presentation explicitly; it does not change fitness.

The sentence after Eq. (6) says to minimise all three equations, contradicting the paper's stated aim of maximising utilisation. Do not implement utilisation minimisation.

### B3. Numerical audit of the 10-task example

Table 1 is consistent with **row = child, column = parent**. That orientation is inferred from the precedence-compatible Figure 5 order and confirmed by the full timing reconstruction; the table caption does not explicitly define it.

Using Tables 1–3 and Figure 5, the hand-worked schedule is:

| Position | Actual task | Processor | Duration | Data ready | Processor ready before task | Start | Finish |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | t1 | P4 | 3 | 0 | 0 | 0 | 3 |
| 2 | t3 | P1 | 4 | 6 | 0 | 6 | 10 |
| 3 | t5 | P1 | 5 | 10 | 10 | 10 | 15 |
| 4 | t7 | P3 | 5 | 16 | 0 | 16 | 21 |
| 5 | t2 | P4 | 4 | 3 | 3 | 3 | 7 |
| 6 | t4 | P1 | 2 | 23 | 15 | 23 | 25 |
| 7 | t6 | P4 | 1 | 33 | 7 | 33 | 34 |
| 8 | t9 | P2 | 1 | 30 | 0 | 30 | 31 |
| 9 | t8 | P4 | 3 | 34 | 34 | 34 | 37 |
| 10 | t10 | P2 | 2 | 44 | 31 | 44 | 46 |

Key calculations:

- t3 receives t1's output at `3 + 3 = 6`.
- t5 follows t3 on P1, so its communication delay is zero and it starts at 10.
- t7 receives t5's output at `15 + 1 = 16`.
- t2 shares P4 with t1 and starts at 3. It can start earlier in clock time than tasks processed earlier in the construction list on other processors.
- t4 waits for `max(7 + 16, 10 + 0) = 23`.
- t6 starts at `25 + 8 = 33`.
- t9 starts at `21 + 9 = 30`.
- t8 waits for `max(34 + 0, 21 + 10) = 34`.
- t10 waits for `max(37 + 7, 31 + 0) = 44` and finishes at 46.

The ten `(start, finish, processor, duration)` rows above match Table 4's ten numeric rows **exactly**. Table 4 instead labels those rows t1, t2, …, t10. Its labels should apparently follow `t1,t3,t5,t7,t2,t4,t6,t9,t8,t10`.

For example, its row labelled t2 assigns P1 and duration 4, even though `W(t2,P1)=3`; those values correctly describe t3. Its row labelled t5 starts at 3 before its apparent predecessor t3 finishes at 15; that row correctly describes t2. The problems disappear with the single consistent row-label interpretation above.

This is strong evidence of a labelling error, not proof of the authors' implementation. Keep the printed table and this reconstructed interpretation distinct in the project record. Figure 6 inherits the same apparent task-label problem.

The resulting metric audit is:

| Quantity | Published | Recalculated from Figure 5 and Tables 1–3 | Finding |
|---|---:|---:|---|
| Completion time | 46 | 46 | Reconciles |
| Execution cost | 64 | `11×1 + 3×7 + 5×2 + 11×2 = 64` | Reconciles using assigned processing time |
| Busy times (P1,P2,P3,P4) | (4,15,5,2), Table 5 | **(11,3,5,11)** | Inconsistent |
| Total busy time | 26 from Table 5 | **30** | Not merely a processor-label permutation |
| Available times (P1,P2,P3,P4) | (44,41,31,42), Table 6 | **(35,43,41,35)** if available means idle within [0,46] | Inconsistent under this natural interpretation |
| Literal Eq. (6) utilisation | 0.85 in Table 7 | **65.217391%** | Does not reconcile |
| Mean processor utilisation | Not clearly defined | **16.304348%** | Explicit normalised metric |
| Speedup and efficiency | 0.14 and 0.035 | Not independently defined by the paper | Cannot validate without a serial reference and definitions |

The per-processor utilisation percentages are approximately `(23.9130,6.5217,10.8696,23.9130)`.

There is an additional numerical pattern: Table 6 equals `46 − B` with Table 5's busy-time vector reversed. Using Table 5's total 26 gives `26/(4×46) ≈ 0.1413`, its complement is about `0.8587`, and another division by four gives about `0.0353`. These resemble Table 7's three final entries but do not establish valid metric definitions. They are a diagnostic observation, not a basis for reverse-engineering undocumented formulas.

**Optimality check:** Put all tasks on P2 in the valid order `t1,t2,…,t10`. All communication delays become zero and the duration is:

\[
4+5+2+1+3+1+2+1+1+2=22.
\]

Its monetary cost is `22×7=154`. Thus 46 cannot be the minimum makespan under the published model. All tasks on P1 give duration **32**, cost **32**, and mean utilisation **25%**, which improve all three metrics relative to the reconstructed Figure 5 schedule. These are feasible arithmetic witnesses, not claims of a global optimum and not proposed additional experimental baselines.

### B4. Larger example and performance claims

Example 2 says four cases but lists five task counts; its parenthesised list repeats 50 where Table 8 gives 70. The five rows are 20, 30, 40, 50 and 70 tasks, with eight processors. Full matrices, DAGs, processor rates and seeds for those instances are not supplied, so exact reconstruction is unavailable from the paper alone. [Paper, §6.2, pp. 3299–3300.]

The paper does not provide a controlled competitor experiment, convergence histories, repeated-run statistics, or an optimality certificate supporting its broader superiority claims. Treat those claims as statements by the authors, not validation criteria already established for this project.

## C. Reproducibility gaps

| Detail | Audit finding | Consequence |
|---|---|---|
| Parent selection | No executable rule or selection pressure specified | Tournament selection is an introduced choice |
| Replacement | Candidate saving is mentioned; population construction is not defined sufficiently | Specify generational replacement and elite handling |
| Elitism | Not explicitly specified | Retaining one elite is a reproduction choice |
| Maximum generations | Maxgn is named; no experimental numeric value supplied | 100 must be labelled as your setting |
| Early termination | Finding the best solution is mentioned without a criterion | Do not invent an optimum test or stagnation cutoff |
| Crossover structure | Whole-portion inheritance is specified | Correct the claim that the split itself remains wholly unclear |
| No-crossover behaviour | Not specified | Define which parent is copied |
| Mutation granularity | Single changed position illustrated; probability granularity unclear | Explicitly choose per-child versus per-gene interpretation |
| Mutation sampling | Replacement distribution and same-value redraw not stated | Specify a different processor and its sampling rule |
| Valid-order generation | Precedence validity required; sampling method absent | Use a documented random topological sorter |
| Duplicate candidates | No policy | Explicitly allow or disallow; allowing is simplest |
| Ties | No rule for fitness ties, parent ties or incumbent ties | Use deterministic documented rules |
| Randomness | No seed, RNG family, input distribution beyond ranges, or run count | Fix RNG and seeds; do not regenerate the published instance |
| DAG generation | Larger-instance graph construction not supplied | Do not claim exact Example 2 reproduction |
| Timing boundaries | Root readiness and some physical assumptions unstated | Define them in the decoder contract |
| Cost and utilisation | Missing assignment indicator; missing utilisation normalisation; inconsistent tables | Document repaired and literal metrics separately |
| Speedup/efficiency | No operational definitions or serial timing reference | Keep outside the current protocol |
| Runtime/platform | No adequate software, hardware or runtime methodology | Record the reproduction environment and timing scope |
| Code/data package | No implementation or reproducibility package linked in the supplied paper | Build from documented equations and tables |

The source-code finding concerns the supplied paper; it is not a claim that no author code exists anywhere. No author correspondence was undertaken. Nothing in the paper establishes tournament selection, elitism, or a particular programming language.

## D. Assumptions we must make

The existing Phase 3 settings are technically reasonable for a small, explainable study. They define a controlled implementation of the paper's approach, rather than an exact reconstruction of its unknown software. The following additions make that implementation unambiguous. **These are recommendations for adoption, not already approved changes to Phase 3.**

| Decision | Recommended explicit convention | Reason/provenance |
|---|---|---|
| Canonical instance | Freeze Tables 1–3; infer edges from positive entries using row-child/column-parent orientation | Reconstructs Figure 5; no per-run data changes |
| Adjacency versus delay | Store directed edges explicitly and attach delays; do not erase same-processor edges | Communication can be zero while precedence still exists |
| Time and rate units | Treat durations/delays consistently as seconds and rates as unspecified monetary units per second | Matches the rate description; no currency is supplied |
| Machine model | All processors available at zero; one non-preemptive task at a time on each processor | Consistent with the scheduling pseudocode |
| Communication model | Fixed delay between differently assigned dependent tasks; no network contention or CPU communication occupancy | The paper models delays, not a separate network scheduler |
| Decoder | Process O once, append to each assigned processor, no gap insertion | Closest to the supplied pseudocode |
| Encoding | D is positional relative to O | Paper-based correction, not a new search method |
| Initial allocation | Each distribution entry sampled uniformly from the four processors | Distribution unspecified; simple completion |
| Initial order | Repeatedly choose uniformly from the currently ready tasks; maintain ready candidates in task-ID order before sampling | Reproducible randomised topological order |
| Selection | Two tournaments, each with 3 distinct population indices; separate tournaments may reuse candidates | Completes the existing tournament-size choice |
| Tournament ties | First drawn candidate among tied minima wins | Reproducible; cost/utilisation remain outside fitness |
| Parent equality | Allow the same individual to win both tournaments | Simplest policy; disclose it |
| Crossover | One child `(D_A,O_B)` with probability 0.95 | Follow the stated paper operator |
| No crossover | Copy both portions of the first selected parent | Missing-paper convention |
| Mutation | Once per non-elite child, probability 0.02; choose one position uniformly and one of the other 3 processors uniformly | Closest simple reading; avoids ineffective same-value changes |
| Replacement | Copy the best current individual; fill the remaining 19 slots with newly generated children | Completes existing elitism 1; population stays 20 |
| Elite and best ties | First minimum in population/evaluation order; replace an incumbent only on strictly lower makespan | Deterministic; no hidden second objective |
| Duplicate chromosomes | Allow them; count every evaluated child against the budget | Avoid added diversity mechanisms and unequal accounting |
| Stop rule | Exactly 100 replacement generations after the initial population; no early stopping | Existing 100-generation choice made precise |
| Cost | Charge only assigned processing time | Explicit repair of Eq. (5) |
| Utilisation | Report both Eq. (6)'s aggregate and the normalised average | Exposes the paper discrepancy transparently |

Random choice among ready tasks does **not** generally sample all topological permutations with equal probability. Describe it accurately and use the same generator in GA initialisation and random search.

Inherited orders remain valid, but the stated crossover and mutation cannot create a task-order sequence absent from the initial population. They can also lose initial order diversity. This is an algorithm limitation to disclose, not a reason to add order mutation during reproduction. Processor changes remain possible, and positional crossover can remap tasks to processors.

The intended mutation rate is consequential: per-child 0.02 gives about `1900×0.02 = 38` mutated offspring in the proposed run. Independent per-gene mutation across 10 positions would instead give about 380 mutation events. Do not leave this interpretation implicit before the later mutation-rate extension.

## E. Frozen experiment specification

### E1. Existing freeze retained

| Item | Value | Origin |
|---|---|---|
| Study framing | Controlled computational reproduction | Phase 1–3 |
| Scope | Example 1, 10 tasks and 4 processors | Paper and Phase 3 |
| Population | 20 | Paper |
| Crossover probability | 0.95 | Paper |
| Mutation probability | 0.02 | Paper |
| Fitness | Minimise completion time | Paper and Phase 3 |
| Generations | 100 | Phase 3 design |
| Runs | 30 | Phase 3 design |
| Seeds | Integers 1–30 | Phase 3 design |
| Selection | Tournament, size 3 | Phase 3 design |
| Elitism | Best 1 retained | Phase 3 design |
| Baseline | Random valid scheduling | Phase 3 design |
| Secondary outputs | Cost and utilisation | Paper and Phase 3 |
| Extension | Deferred until reproduction works | Phase 3 |

The internal processor-vector crossover described in the handoff is recorded as the **previous proposal, now superseded by the user's approval of the paper-based correction**. The adopted operator inherits the whole processor portion of one parent and the whole task order of the other. Its implementation remains deferred to Phase 4.4. No mutation-rate sweep or multi-objective GA is introduced.

### E2. Canonical input transcription for Phase 4.1

Tasks are t1–t10; processors are P1–P4. The computation-duration matrix from Table 2 is:

| Task | P1 | P2 | P3 | P4 |
|---|---:|---:|---:|---:|
| t1 | 4 | 4 | 4 | 3 |
| t2 | 3 | 5 | 5 | 4 |
| t3 | 4 | 2 | 5 | 5 |
| t4 | 2 | 1 | 4 | 4 |
| t5 | 5 | 3 | 5 | 4 |
| t6 | 5 | 1 | 3 | 1 |
| t7 | 1 | 2 | 5 | 4 |
| t8 | 1 | 1 | 4 | 3 |
| t9 | 4 | 1 | 3 | 5 |
| t10 | 3 | 2 | 4 | 4 |

Processor rates from Table 3 are **P1 = 1, P2 = 7, P3 = 2, P4 = 2**.

The 12 directed edges and their delays, transcribed from Table 1 using the audited orientation, are:

| Parent | Child | Delay |
|---|---|---:|
| t1 | t2 | 18 |
| t1 | t3 | 3 |
| t2 | t4 | 16 |
| t3 | t4 | 14 |
| t3 | t5 | 12 |
| t4 | t6 | 8 |
| t5 | t7 | 1 |
| t6 | t8 | 12 |
| t7 | t8 | 10 |
| t7 | t9 | 9 |
| t8 | t10 | 7 |
| t9 | t10 | 16 |

All other entries in the published communication table are zero and interpreted as absent edges for this instance. t1 is its sole source; t10 is its sole sink. Both ascending task IDs and Figure 5's order are valid topological orders. Keep the original positive edge delay even if a particular allocation makes its effective delay zero.

These published inputs are fixed across all runs and both algorithms. Randomly drawing a fresh instance from the paper's ranges would change the experiment.

### E3. Proposed completion of run and baseline accounting

With one copied elite and 19 evaluated offspring per replacement generation:

\[
\text{candidate evaluations}=20+100(20-1)=\mathbf{1920}.
\]

This is a proposed exact budget, conditional on adopting Section D's replacement rule. The paper does not specify it. Reuse the unchanged elite's score; do not count copying it as a new evaluation. Repeated or unchanged child chromosomes still count because they consume candidate evaluations. Avoid fitness caching in the initial simple implementation.

Give random search **1920** valid candidate evaluations per run and retain its best candidate seen. A baseline of only 20 random candidates, or one candidate, would not be equivalent to the proposed GA budget. If implementation deliberately generates 20 new children before survivor selection, recalculate the GA budget and match the baseline; do not mix those conventions.

**Proposed pairing:** for run seed s, give both methods the same initial 20 chromosomes. Random search then evaluates 1900 additional independently generated candidates; the GA performs its 100 generations. Use separate RNG objects initialised consistently from s so one algorithm cannot consume the other's RNG state. The paired initial populations are intentional; the 30 seed-labelled runs assess stochastic variability on one fixed instance. Specify the generator and record its software version when implementation begins.

Generation 0 records the evaluated initial population. GA traces contain 101 checkpoints, 0–100. Record random-search incumbents at the equivalent evaluation counts `20 + 19g`, so convergence comparisons use candidate evaluations as the shared horizontal axis.

### E4. Proposed reporting contract

For each method and seed, retain the final incumbent chromosome, decoded task allocation, schedule trace, makespan, execution cost, processor busy times, both utilisation measures, evaluation count and runtime. Cost and utilisation must belong to the **same makespan-selected incumbent**, rather than separately chosen best values.

For the GA, store best and mean population makespan at each generation; also retain a best-so-far value if needed for clear reporting. With elitism, best population fitness should be non-increasing. Random search stores its best-so-far trace.

Across the 30 final makespans, report minimum, maximum, mean, median and **sample standard deviation** with denominator 29. Summarise cost, utilisation and runtime separately and label their units. Keep full numeric precision internally; round only displays.

Use paired per-seed differences `GA makespan − random-search makespan`, with negative values favouring GA. Report wins, ties and losses, plus the mean and median difference. A significance test is optional and must be declared before inspecting results if used. Do not make an inferential claim solely from one best run.

Measure algorithm wall time consistently, including initialisation and evaluations, excluding plotting and file export. If the common initial population is precomputed, either include equivalent initialisation work for both timings or label both timings as search-only. Record machine, OS, interpreter and relevant package versions. Fixed seeds should reproduce outputs and histories in the same pinned environment; exact runtimes are not expected to repeat.

Useful evidence remains the requested convergence plot, GA/random comparison, final schedule table and summary statistics. When selecting a schedule for the report, declare the rule, such as lowest GA makespan across runs and smallest seed to break ties. Distinguish that best case from the 30-run summary.

## F. Phase 4 implementation architecture

Use small modules with explicit inputs and outputs. Python is a reasonable proposed implementation language because the core needs only straightforward data structures, random sampling and arithmetic. The user has not yet specified a language; this report does not freeze a language or create a software environment.

| Phase | Responsibility | Main outputs | Exit condition |
|---|---|---|---|
| 4.1 | Data loading and validation | Task IDs, processor IDs, 12 edges, 10×4 durations, 4 rates, source metadata | Transcription checked against Tables 1–3; graph validated |
| 4.2 | Deterministic schedule evaluation and metrics | Task timing trace, makespan, busy times, cost and utilisation | Small manual case and Figure 5 reconstruction agree |
| 4.3 | Candidate representation, generation and validation | Positional chromosomes; random valid task orders | Generated candidates always satisfy representation and precedence rules |
| 4.4 | Selection, crossover, mutation and elite replacement helpers | Independently testable operator outputs | Operator contracts verified before integration |
| 4.5 | GA loop | Final incumbent, 101-point traces, evaluation accounting | Population and elitism invariants hold; seeded replay works |
| 4.6 | Experiment runner | Raw results for 30 seed-labelled GA runs | Saved configuration, environment and outputs make reruns auditable |
| 4.7 | Equal-budget random search and reporting | Matched baseline results, paired comparisons, concise figures/tables | Fairness/accounting checks pass; conclusions reflect all runs |

Suggested eventual files are `problem.py`, `scheduler.py`, `chromosome.py`, `operators.py`, `ga.py`, `baseline.py`, `experiment.py` and `reporting.py`, plus a small data file, configuration file and tests. These are architectural suggestions only; none has been created in Phase 4.0.

The scheduler must be a deterministic function of the problem and chromosome. It must not contain selection, randomness or plotting. Both algorithms must call the same evaluator and use the same valid-candidate generator for random initialisation. Keep problem data immutable and avoid shared mutable parent/child arrays.

Store enough detail per scheduled task to explain every calculation: its predecessors, each effective communication delay and arrival, data-ready time, processor-ready time before placement, start, finish, duration and charge. A single trace table is more useful for a demonstration than a large framework.

## G. Validation/testing strategy

### G1. Phase 4.1: verify the problem before algorithms

Check exactly 10 unique task IDs, 4 unique processor IDs, 40 positive durations, 4 rates and 12 unique directed edges. Reject unknown endpoints, self-loops and cycles. Verify the sole source t1, sole sink t10 and both known valid orders. Compare every transcribed value with the PDF; range checks alone cannot catch a transposed or mistyped value.

For future generic data, adjacency must remain distinct from delay values so zero-delay precedence edges can be represented. Do not infer generic graph structure solely from whether delay is nonzero.

### G2. Phase 4.2: independent small hand-worked example

This is a deliberately constructed validation fixture, not a second research instance. Two processors have rates P1 = 2 and P2 = 5.

| Task | Duration on P1 | Duration on P2 |
|---|---:|---:|
| t1 | 2 | 4 |
| t2 | 3 | 2 |
| t3 | 6 | 4 |
| t4 | 2 | 1 |

Edges are `t1→t3:4`, `t2→t3:3`, `t3→t4:5`. Use order `(t1,t2,t3,t4)` and positional distribution `(P1,P1,P2,P2)`.

| Task | Predecessor arrivals | Data ready | Processor ready | Start | Finish |
|---|---|---:|---:|---:|---:|
| t1 | None | 0 | 0 | 0 | 2 |
| t2 | None | 0 | 2 | 2 | 5 |
| t3 | t1: 2+4=6; t2: 5+3=8 | 8 | 0 | 8 | 12 |
| t4 | t3: 12+0=12, same processor | 12 | 12 | 12 | 13 |

Expected makespan is **13**, busy times are **(5,5)**, cost is **35**, aggregate utilisation is **76.923077%**, and mean processor utilisation is **38.461538%**. This tests a root waiting for its processor, a join taking the maximum arrival, different-processor communication and same-processor delay cancellation.

Explain this trace manually before continuing to chromosome generation. Also test a one-task case, unused processors, disconnected roots and a zero-delay precedence edge.

### G3. Paper-based evaluation checks

Use Figure 5 as a deterministic regression fixture with the corrected task labels described in B3. Expected values are makespan 46, cost 64 and busy times `(11,3,5,11)`. Do **not** encode Table 5's incorrect busy times or Table 7's 0.85 as expected behaviour.

Use the all-P1 and all-P2 schedules as additional independent checks: `(makespan,cost)=(32,32)` and `(22,154)`. They verify same-processor communication cancellation and demonstrate why 46 is not an optimum target.

For every evaluated schedule, independently verify:

- Each task executes exactly once on its assigned processor.
- `finish − start` equals the correct duration-matrix entry.
- Every precedence edge satisfies `child start ≥ parent finish + effective delay`.
- Task intervals on the same processor do not overlap.
- Makespan equals the largest finish time, and each processor ready time equals its last finish time.
- Total busy time equals the sum of assigned durations; cost agrees by both task and processor aggregation.
- Per-processor and mean utilisation lie between 0% and 100%; aggregate utilisation can reach 100N%.

### G4. Chromosome and operator checks

Reject missing, duplicate or unknown tasks; invalid processor IDs; unequal portion lengths; and precedence-invalid orders. Generate many seeded candidates to check validity, while recognising that repeated random checks alone are not a proof of correctness.

Use small known parents to verify exact whole-portion inheritance. Test operator probability boundaries 0 and 1, plus the configured values. These boundaries are unit checks, not a mutation-rate experiment. Confirm mutation changes exactly one distribution entry when triggered, chooses a different processor, preserves O and does not alter either parent.

Test tournament direction on known makespans, deterministic ties, one copied elite, population size 20, and the specified no-crossover path. Topological-order preservation should follow directly from the operators' contracts rather than from a penalty mechanism.

### G5. Integrated experiment checks

Check exactly 100 replacement generations, 101 recorded GA checkpoints and 1920 candidate evaluations under the proposed accounting. Verify the baseline has the same budget and initial population. Elite copying must preserve a non-increasing best-fitness trace; it does not guarantee a strict improvement in every generation or run.

Repeat the same seed and configuration to verify identical chromosomes, schedules, metrics and convergence histories. Exclude runtime from equality checks. Check that each saved result records the seed and input/configuration identity, and that output files cannot silently mix configurations.

For tiny test instances only, enumerate all assignments and valid orders if needed to establish an evaluator check or known optimum. This is a validation aid; it is not necessary to solve the 10-task research instance exhaustively or add a new optimiser.

**Research success criterion correction:** correctness, reproducibility and honest reporting are mandatory. A favourable GA-versus-random result is a hypothesis to test. If the GA ties or loses, report that outcome and inspect implementation validity without changing the frozen settings merely to obtain a preferred conclusion. A valid controlled reproduction can produce a negative performance result.

## H. Remaining risks or questions

### H1. What must be settled before each next phase

| Point | Resolution proposed in this report | When it matters |
|---|---|---|
| Input authority | Tables 1–3 are canonical; later result tables are evidence to audit, not substitute input | Before Phase 4.1 |
| Table 1 orientation | Store row-child/column-parent values as explicit parent→child edges | Before Phase 4.1 |
| Units and data schema | Separate durations, edge delays and processor monetary rates | Before Phase 4.1 |
| Language/environment | Choose a simple implementation stack and record the version | At Phase 4.1 setup |
| Positional representation and decoder | Use `a(o_k)=d_k` and append-only scheduling | Before Phase 4.2 |
| Cost/utilisation semantics | Assigned-time cost; separately labelled aggregate and normalised utilisation | Before Phase 4.2 |
| Crossover correction | Adopt the paper's whole-portion operator, or explicitly declare the simplified alternative a deviation | Before Phase 4.4 |
| Mutation and selection conventions | Per-child single-position mutation and the detailed tournament/tie rules | Before Phase 4.4 |
| Replacement and evaluation budget | One elite plus 19 offspring; 1920 evaluations; paired baseline | Before Phases 4.5–4.7 |

There is no missing numeric input preventing the proposed 10-task data layer. The readiness issue is making its interpretation explicit and recording adoption of the paper-based corrections. Resolving the authors' unavailable software, speedup definition, larger datasets, or true global optimum is not a prerequisite for Phase 4.1.

### H2. Material limitations to disclose

One fixed small DAG supports conclusions about the chosen instance and stochastic search behaviour, not broad claims about cloud systems. Large communication delays relative to task durations can favour putting many tasks on one processor. A higher utilisation percentage can reflect longer processing on slower processors; with heterogeneous durations it is not automatically evidence of a better makespan or lower cost.

The paper's order operators restrict exploration to initial order sequences. Selection, mutation granularity and replacement choices can materially affect results. The proposed settings are sensible and explainable but are not recoverable facts about the authors' implementation.

The corrected interpretation of Table 4 is strongly supported by the arithmetic, but has not been confirmed by the authors. Keep that inference labelled. Busy-time, utilisation and speedup discrepancies should remain in the deviation record rather than being concealed by special-case formulas.

**Phase 4.0 deliverable is complete and approved:** the source has been audited, inputs and a reference schedule have been transcribed, and the remaining design decisions are explicit. Phase 4.1's fixed data layer is also approved. The user has authorised Phase 4.2's deterministic scheduler, metrics and three published-data validation cases. Phase 4.3 and all subsequent phases require separate approval; Phase 5 remains deferred.
