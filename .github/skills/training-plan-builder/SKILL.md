---
name: training-plan-builder
description: Review, design, create, or align technology training plans with progressive explanations, module-specific guided labs, independent exercises, verification, and explicit starting states. Use for new workshops, training updates, curriculum consistency, and module pilots.
---

# Training plan builder

Build coherent, practical training that prepares learners to apply a technology,
not merely run completed examples. Use this repository's module structure across
topics while preserving technology-specific tools, scenarios, and platform needs.

## Collaboration stage and scope

- Inspect the actual guides, examples, setup, tests, and validation notes first.
  Include relevant newer training branches when reviewing unfinished integration.
- For a review or proposal, provide findings and a concept-to-exercise map before
  editing. For an approved pilot, change only that module and its dependent links,
  exercise, solution, and validation notes. Do not migrate all workshops implicitly.
- Establish audience, intended capabilities, scenario, required/optional services,
  platform choices, cost drivers, and existing learner knowledge from evidence.
  Ask one focused question only for a consequential unresolved choice.
- Preserve existing implementations unless a learning objective requires a change.
  Do not add providers, services, paid runs, frameworks, or assessments without
  authorization. Commit, push, merge, or publish only when requested.

## Shared learning contract

Every module must connect **concept -> guided lab -> independent exercise ->
evidence -> interpretation**. Use
[the module template](templates/module.md) as the canonical structure.

- Teach unfamiliar terms before commands depend on them. Start from a familiar
  problem, introduce a small example, then expand the architecture gradually.
- State observable outcomes. A process starting, a test passing, or an agent
  returning does not by itself prove the business outcome.
- Use a continuing scenario. Include a relevant diagram and explain what its
  arrows represent; do not make a decorative diagram substitute for explanation.
- State prerequisites and the exact starting state: working directory, terminal,
  active services, variables, data, and IDs. Name prior-module dependencies.
  Modules may be sequential; do not claim independent execution without resets.
- Explain the guided steps, then give a bounded exercise with reduced guidance.
  Operating completed code is a demonstration, not an independent coding exercise.
  Foundations can instead use diagramming, prediction, or evidence classification.
- Include a failure/variation that tests the concept, with expected error behavior
  and whether data changes. Avoid irrelevant fault injection just to fill a section.
- Require specific evidence and interpretation, not screenshots alone. Separate
  actions, expected observations, and checks that establish the outcome.
- Provide targeted troubleshooting and a scoped reset. Identify what must remain
  for the next module; never erase shared learner state as generic cleanup.
- Keep reference solutions outside the learner task. Link them after the exercise.
  Public solutions support self-study; private grading material must remain private.

## Training organization

Use [the training overview template](templates/training-overview.md). Favor:

```text
<technology>/
  README.md
  training-guide.md
  setup/
  modules/
    01-<topic>/README.md
  examples/
  exercises/
  solutions/
  fixtures/
  infrastructure/
  troubleshooting.md
  VALIDATION.md
```

Create directories only when they have real content. Share runtime code and
fixtures instead of copying them into each module. Keep `training-guide.md` as
the roadmap once modules are extracted: link to canonical module text rather
than maintaining two copies. During a pilot, retain untouched guide sections.

Declare one working-directory convention per workshop and use it in every
module. Preserve a workshop's current convention during a narrow migration;
coordinate a full path migration rather than mixing roots.

For framework tracks, share concepts and outcome criteria while keeping
framework-native orchestration and clearly labelled commands.

## Writing and platform rules

- Describe scope, skills gained, capstone, depth, and cost/resource drivers.
  Do not add durations, schedules, day groupings, or completion estimates.
- Avoid repeated generic "not production" or dummy-data disclaimers. Put specific
  operational guidance next to risky actions, credential setup, or paid calls.
  Retain concrete facts learners need to execute responsibly.
- Provide explicit supported-shell commands; do not ask learners to translate
  PowerShell into Bash. If the Python task is common, give separate launch
  commands and shared Python source. Distinguish host paths from container paths.
- Label placeholders, reuse returned IDs, preserve header quoting, and avoid
  relying on unknown total counts from prior runs.
- Distinguish documented targets from exercised platforms. Mock tests do not
  establish live-provider behavior. Model output checks should assess evidence,
  controls, and stopping, not exact prose.
- Paid services require an explicit choice and documented usage/cost drivers.
  Never invent keys, silently switch providers, or imply an exact spend cap.

## Workflow

1. **Review:** Identify existing strengths and gaps using actual modules and code.
2. **Map:** List each module's outcome, prerequisites, concept, lab, independent
   task, failure/variation, and evidence. Avoid forcing identical module counts.
3. **Prepare:** Reuse or supply setup/readiness instructions with clear choices,
   resource requirements, and consistent working directories.
4. **Author:** Fill the module template, implement any needed starter/reference
   code, and update roadmap links. Eliminate unresolved template placeholders.
5. **Validate:** Follow the module as a learner. Execute the smallest relevant
   tests, commands, negative cases, resets, and handoff where possible.
6. **Review:** Apply [the review checklist](references/review-checklist.md) and run:

   ```text
   python .github/skills/training-plan-builder/scripts/check_module.py <module-README>
   ```

   This standard-library checker verifies structure, basic links, fences, and
   duration/placeholder rules. It does not execute labs, render Mermaid, prove
   platform support, or assess teaching quality.
7. **Record:** Update the workshop's `VALIDATION.md` with what was executed,
   versions/environment where relevant, and anything not exercised. Report the
   changed module and any learner prerequisites or limitations concisely.

For an existing workshop, pilot one representative module before applying the
format broadly. Do not infer approval for repository-wide migration from a pilot.
