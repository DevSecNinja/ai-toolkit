# Recommended processing and merge order

This is an advisory output contract for the reviewing agent, **not** a new
helper command, scoring system or extension to `plan.json`. Recommend the work
needed to process the backlog, not just the PRs that can merge today. Rankings
never supply evidence, clear a gate or authorize a write.

## Build the sequence from evidence

Use current inspections plus the seven review evidence categories in
`SKILL.md`. Cite immutable head/target file references and source findings;
do not infer priority or compatibility from PR titles alone.

1. **Separate readiness from urgency.** A merge-ready-now recommendation needs
   complete high-confidence review, verified manual status and all current
   helper gates satisfied. Conditional entries remain `hold`, with each repair,
   missing evidence item or policy blocker named. Enabled automerge entries are
   excluded from manual selection even when failing or waiting; unknown status
   requires configuration/provenance review.
2. **Identify real prerequisites.** Trace runtime/build consumers and version
   constraints on the reviewed target. An adapter that must support a compiler
   before its upgrade is a prerequisite; two PRs merely touching the same
   lockfile are not necessarily dependent. Explain what the shared change means
   (incompatible resolution, likely rebase churn, or no known conflict).
   Distinguish a merge prerequisite from an evidence/repair task. If the link
   is unverified, say so and recommend the specific investigation instead of
   inventing an edge. Conflicting/circular constraints need a separately
   authorized compatible repair, not an arbitrary order.
3. **Order feasible work.** Prerequisites precede dependent merges. For
   independent work, use evidenced urgency (for example, a verified security
   impact or an approaching support deadline), present readiness, consumer
   exposure, migration risk and expected shared-file churn. State the tradeoff
   rather than assigning a numeric score. An urgent blocker can be investigated
   promptly while an unrelated ready PR proceeds; it must not hold up every
   repository. Nor should a low-risk patch automatically outrank a well-reviewed
   major. When evidence supplies no preference, use lowercase `owner/repo` then
   numeric PR number and explicitly call it an **independent tie-break**, not a
   prerequisite. Reassess the preference when evidence changes.
4. **Name the next action and its exit condition.** "Fix CI" is insufficient:
   identify the job/constraint/consumer, what to inspect or repair, what result
   would clear it, and what would still remain. For a policy hold, distinguish
   deciding whether to pursue a separate policy change from that change actually
   being implemented and validated. User agreement alone never changes a guard.
   No remediation, rerun, rebase or policy edit is implicitly authorized.

Do not hardcode repo, package or workflow-action ordering. Whether checkout,
runtime setup, a labeler or a compiler should come first depends on the actual
workflow consumers, runtime requirements, compatibility and evidence. PR age
and semver labels can describe an update but cannot establish its safety or
priority. Dashboard inactivity is not verified security urgency.

### Diagnose skipped jobs versus disabled workflows

GitHub can disable **scheduled workflows in public repositories after 60 days
without repository activity**; this is different from an active workflow
intentionally skipping jobs through `if` conditions or false reusable-workflow
inputs. Inspect the workflow's current state, event triggers, source conditions
at the reviewed head/target and actual run/check metadata before attributing a
missing execution to inactivity. An `active` workflow list does not establish
that the relevant jobs ran or tested the changed consumers.

When source-configured optional skips are verified, report that cause instead
of proposing workflow reactivation as a fix. When inactivity disablement is
verified, report the missing coverage and propose separately authorized
reactivation/evaluation if appropriate. Neither case counts as successful
execution or permits bypassing the skipped/absent-check policy. No enable,
rerun or policy-change action follows automatically from this diagnosis.

Source: [GitHub workflow disablement](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows).

## Required report

Lead with: **First recommended action: ...** and **Merge-ready now: ...**.
If the first action is a decision or repair, say what needs separate permission.
If a PR is ready, propose its exact merge/queue action for confirmation, not
execution. Queue-ready still means a request to enqueue, never a promise of
merge. Where evidence is incomplete, the first action can be a concrete
read-only inspection.

Use a compact ordered table, keeping existing review details or linking them
from the row:

| Order | PR / action and reviewed head / target | Readiness / confidence                | Why here / evidence                   | Prerequisites or independence                                     | Blockers and concrete next action                      |
| ----- | -------------------------------------- | ------------------------------------- | ------------------------------------- | ----------------------------------------------------------------- | ------------------------------------------------------ |
| 1     | Specific scoped PR or investigation    | Merge-ready now or conditional / hold | Source-backed urgency, risk and churn | Named prerequisite with exit condition, or independent preference | Exact action, remaining gates, and permission boundary |

Include versions/change type, PR links and full head/target SHAs in the review
detail; do not invent missing SHAs. A row may represent an investigation before
a later conditional merge of the same PR. Label those actions distinctly.
Specify a **proposed future merge order**, including conditional entries, apart
from the **currently eligible confirmation selection**. "Ready now" still
requires exact consent and just-in-time preflight. Necessary prerequisites
must be satisfied and reviewed before dependents enter that selection; do not
select an unmet dependent for later in the same batch.

Show automerge-managed exclusions separately with enabled/waiting/failing/queued
health, evidence and the next read-only check. Keep unknown status visible as
held, not manual. Show dashboard replacement/remediation recommendations in
their own table, not as hidden merge entries.

If all manual PRs are held, say **no executable selection** but still produce
an ordered unblock sequence and conditional future merge order with reasons.
Do not offer blanket approval of the future order, emit approval artifacts, or
claim that a policy exception is already available.

## Synthetic example: all manual candidates held

Illustrative evidence, not live repository facts or authorization:
`fixture:workflow-diffs@head` and `fixture:consumers@target` show PR 18 only
changes a label workflow covered by its successful tests; PR 51 changes runtime
setup in a release workflow not exercised on PRs. Neither consumes the other,
their files are separate, and no compatibility dependency is identified.
`fixture:checks@head` has successful required jobs but six intentionally
skipped optional jobs on both PRs. `fixture:peer-log@head` shows PR 27's compiler
is outside its lint adapter's peer range; it also lacks migration evidence.

**First recommended action:** inspect the six skipped jobs' conditions and the
effective check policy read-only, then ask whether to pursue a separate,
narrow policy-change proposal. **Merge-ready now: none.** GitHub `CLEAN` does
not override the current helper's skipped-check hold.

| Order | PR / action                                                  | Readiness          | Reason and prerequisite                                                        | Blocker / next action                                                                                                                                           |
| ----- | ------------------------------------------------------------ | ------------------ | ------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1     | Diagnose shared skipped-check policy for PRs 18 and 51       | Hold               | Common blocker in `fixture:checks@head`, not a dependency between the PRs      | Verify optional-job conditions; preserve hold. A separate policy proposal needs permission, implementation and validation before any changed eligibility claim. |
| 2     | Reevaluate PR 18 after the blocker is actually resolved      | Conditional / hold | Narrow, already covered diff; independent preference over PR 51, not mandatory | Refresh all checks/rules/config and review on current head/target; only then propose exact consent if eligible.                                                 |
| 3     | Obtain release-consumer evidence for PR 51                   | Conditional / hold | `fixture:consumers@target` exposes a non-PR coverage gap                       | Inspect release runner/runtime compatibility and relevant run evidence. Any isolated execution requires separate authorization; policy hold also remains.       |
| 4     | Investigate compatible compiler/adapter resolution for PR 27 | Conditional / hold | Verified peer-range conflict in `fixture:peer-log@head`; not "major last"      | Find a supported combination, propose a separately authorized manifest/lockfile repair and migration checks; do not just regenerate an incompatible lockfile.   |

**Proposed future merge preference:** 18, then 51, then 27, each only after its
own gates clear and a fresh review. This example assumes no verified urgency;
18/51 are independent, and 27 needs a compatible repair, not either workflow
PR. Investigations can proceed independently; this numbering does not prohibit
earlier compiler repair or make PR 18 a prerequisite for runtime setup.
**Currently eligible confirmation selection: none.**

An enabled artifact PR waiting on release stability or reporting a registry
error belongs in the separate automerge health table. Recommend verifying its
release-age/config/log evidence, not manually selecting it. A dashboard
replacement proposal likewise needs its own scoped authorization.

## Move from recommendations to processing

Follow the [handoff contract](handoff.md): keep holds in the review, choose only
eligible entries, validate the exact v2 plan and show its digest, full selected
head SHAs, target SHAs, actions and order before asking for confirmation.
Never copy the entire advisory sequence into `approval.json` or `--select`.
After actual consent, use the bundled helper, not an alternate merge route.

A successful prerequisite merge changes what should be reviewed next; it does
not preapprove a dependent. After merges or PR/base changes, reinspect affected
remaining entries, including shared lockfiles/workflows and changed consumers.
Wait for fresh CI/reviews as needed, reevaluate rules/config and update the
advisory sequence. Apply the v2 freshness/digest rules and obtain new exact
confirmation for a regenerated plan. Already-confirmed, unaffected independent
repositories need no fictional prerequisite, but must pass their own current
preflight. A queued or uncertain write stops the batch; queued is not merged.
