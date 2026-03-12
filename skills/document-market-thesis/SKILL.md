---
name: document-market-thesis
domain: cave
subdomain: market-analysis
category: preflight
description: Create comprehensive market thesis documentation for new product categories
---

# Document Market Thesis

## What This Skill Does

Guides you through creating a complete market thesis documentation package for a new product category. Produces 7-8 structured documents that explain the market at every level.

## When To Use

- Launching a new product category (not just a product)
- Need to explain "why this market exists now"
- Need documentation that covers technical, economic, personal, and democratization angles
- Want a reference package that future instances can read and understand

## The Structure

Your market thesis documentation should have these files:

| File | Purpose |
|------|---------|
| `00_overview.md` | Thesis statement, why now, file index |
| `01_death_of_old_model.md` | Why the old way fails (transfer, context, motivation) |
| `02_product_as_category.md` | What the new thing actually IS |
| `03_progression_system.md` | How users advance/complete (gamification) |
| `04_economics.md` | Cost structures, subsidies, viability |
| `05_origin_story.md` | Your journey, the struggle, the pivot |
| `06_democratization.md` | Barriers, phases, vision, end state |
| `07_complete_picture.md` | Full stack, flow diagram, comparison table, one-liner |

## The Pattern

Each document follows:
1. **State the problem** with the old model
2. **Show why it fails** (specific failure modes)
3. **Present the new model** (what changes)
4. **Prove viability** (economics, evidence)
5. **Show the path** (how we get from here to there)

## Reference Implementation

See `/tmp/launch_v0/new_market/` for a complete example documenting AI-native infoproducts.

## How To Use

1. Create directory: `/path/to/project/new_market/`
2. Write each file following the structure above
3. Start with `00_overview.md` (forces you to clarify thesis)
4. End with `07_complete_picture.md` (forces you to synthesize)
5. Each file should stand alone but connect to others

## The One-Liner Test

By the end, you should have a one-liner that captures the entire thesis.

Example: "PAIA infoproducts are courses you do WITH an AI agent that result in you having a working AI agent."

If you can't write that one-liner, your thesis isn't clear yet.
