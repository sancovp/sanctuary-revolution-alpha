# Conversation Ingestion Phase 5-8 Implementation Plan

## Overview

Frameworks are JSON files on disk. Metastack loads JSON, renders to markdown. You edit JSON to change content. State tracks metadata + paths.

---

## Phase 5: Emergent Framework Creation

**Purpose:** Create individual framework documents from synthesized IO pairs.

### Tool: `create_emergent_framework(name, strata)`
- Creates JSON file at `$HEAVEN_DATA_DIR/frameworks/emergent_{name}.json`
- JSON skeleton matches EmergentFramework metastack model:
  ```json
  {
    "name": "...",
    "strata": "...",
    "obstacle": "",
    "dream": "",
    "definitions": "",
    "process": "",
    "diagrams": "",
    "examples": ""
  }
  ```
- Logs metadata in state (name, strata, path, created_at, status: "draft")
- Returns path

### Tool: `preview_emergent(name, output_path)`
- Loads JSON from known path
- Passes to metastack, renders to markdown
- Writes to `output_path`
- Returns path so user can read it

### Workflow
1. User runs `create_emergent_framework("XYZ", "paiab")`
2. Gets back path to JSON
3. Edits JSON (fills in obstacle, dream, definitions, process, etc.)
4. Runs `preview_emergent("XYZ", "/tmp/preview.md")` to see rendered output
5. Iterates until satisfied
6. Marks as complete (ready for Phase 6)

---

## Phase 6: Journey Metadata

**Purpose:** Finalize the journey framing for emergent frameworks.

### What happens
- Emergent JSON already has obstacle/dream fields from Phase 5
- Phase 6 is review/finalization - confirming the journey framing is correct
- May involve refining obstacle/dream based on how emergent fits into larger picture

### Tool: `finalize_emergent_journey(name)`
- Validates obstacle and dream are filled
- Marks status as "journey_complete"
- Now eligible for assignment to canonical

### Tool: `assign_emergent_to_canonical(emergent_name, canonical_name)`
- Links emergent to canonical
- Stores in state: `emergent.canonical_framework = canonical_name`

---

## Phase 7: Canonical Framework Composition

**Purpose:** Compose emergent frameworks into higher-order canonical frameworks.

### Tool: `create_canonical_framework(name, strata, emergent_names)`
- Creates JSON file at `$HEAVEN_DATA_DIR/frameworks/canonical_{name}.json`
- JSON skeleton:
  ```json
  {
    "name": "...",
    "strata": "...",
    "obstacle": "",
    "dream": "",
    "bridging_explanation": "",
    "emergent_refs": ["emergent_Something.json", "emergent_Another.json"]
  }
  ```
- If only ONE emergent: `bridging_explanation` stays empty, emergent content passes through
- If MULTIPLE emergents: `bridging_explanation` required to tie them together
- Logs metadata in state
- Returns path

### Tool: `preview_canonical(name, output_path)`
- Loads canonical JSON
- For each emergent_ref: loads that JSON, renders it
- Assembles full document:
  - Canonical obstacle/dream
  - Bridging explanation (if multiple)
  - Each emergent framework rendered inline
- Writes to `output_path`
- Returns path

### Workflow
1. User identifies which emergents compose into a canonical
2. Runs `create_canonical_framework("ABC_for_XYZs", "cave", ["emergent1", "emergent2"])`
3. Gets back path to JSON
4. Edits JSON (fills in obstacle, dream, bridging_explanation)
5. Runs `preview_canonical("ABC_for_XYZs", "/tmp/preview.md")`
6. Iterates until satisfied
7. Marks as complete (ready for Phase 8)

---

## Phase 8: Publishing

**Purpose:** Render final documents and push to substrates.

### Tool: `render_canonical_for_publishing(name, output_path)`
- Final render of canonical to markdown
- This is the "blessed" version that gets published
- Returns path

### Tool: `generate_derivative_content(canonical_name, derivative_type)`
- Creates derivative documents from canonical
- Types: "twitter_thread", "linkedin_post", "youtube_description", etc.
- Each has its own metastack template
- Returns path to derivative JSON
- User edits, previews, finalizes

### Tool: `publish_to_substrate(canonical_name, substrate)`
- Takes canonical (and any derivatives)
- Passes paths to substrate projector
- Substrate projector uses n8n to push to:
  - Discord (journey channel + framework channel)
  - Twitter
  - LinkedIn
  - YouTube
  - etc.
- Marks canonical as published in state

### Workflow
1. `render_canonical_for_publishing("ABC_for_XYZs", "/final/abc.md")`
2. `generate_derivative_content("ABC_for_XYZs", "twitter_thread")` -> edit -> preview
3. `generate_derivative_content("ABC_for_XYZs", "linkedin_post")` -> edit -> preview
4. `publish_to_substrate("ABC_for_XYZs", "discord")`
5. `publish_to_substrate("ABC_for_XYZs", "twitter")`
6. etc.

---

## Metastack Templates Needed

### 1. EmergentFramework
```python
class EmergentFramework(MetaStack):
    name: str
    strata: str
    obstacle: str
    dream: str
    definitions: str
    process: str
    diagrams: Optional[str] = None
    examples: Optional[str] = None

    def render(self) -> str:
        output = f"# {self.name}\n\n"
        output += f"## Obstacle\n{self.obstacle}\n\n"
        output += f"## Dream\n{self.dream}\n\n"
        output += f"## Definitions\n{self.definitions}\n\n"
        output += f"## Process\n{self.process}\n\n"
        if self.diagrams:
            output += f"## Diagrams\n{self.diagrams}\n\n"
        if self.examples:
            output += f"## Examples\n{self.examples}\n\n"
        return output
```

### 2. CanonicalFramework
```python
class CanonicalFramework(MetaStack):
    name: str
    strata: str
    obstacle: str
    dream: str
    bridging_explanation: Optional[str] = None
    emergent_refs: List[str]  # paths to emergent JSONs

    def render(self) -> str:
        output = f"# {self.name}\n\n"
        output += f"## Obstacle\n{self.obstacle}\n\n"
        output += f"## Dream\n{self.dream}\n\n"

        if self.bridging_explanation:
            output += f"## Overview\n{self.bridging_explanation}\n\n"

        output += "---\n\n"

        # Load and render each emergent inline
        for ref in self.emergent_refs:
            emergent_json = load_json(ref)
            emergent = EmergentFramework(**emergent_json)
            output += emergent.render()
            output += "---\n\n"

        return output
```

### 3. Derivative templates (Phase 8)
- TwitterThread
- LinkedInPost
- YouTubeDescription
- etc.

---

## File Structure

```
$HEAVEN_DATA_DIR/frameworks/
  emergent_XYZ.json
  emergent_ABC.json
  emergent_DEF.json
  canonical_Big_Thing.json
  canonical_ABC_for_XYZs.json
  derivative_ABC_for_XYZs_twitter.json
  derivative_ABC_for_XYZs_linkedin.json
```

One flat folder. Naming convention distinguishes type: `emergent_`, `canonical_`, `derivative_`.

---

## State Tracking

State stores metadata, not content:

```json
{
  "emergent_frameworks": {
    "XYZ": {
      "path": "frameworks/emergent_XYZ.json",
      "strata": "paiab",
      "status": "draft|journey_complete|assigned",
      "canonical_framework": "Big_Thing"
    }
  },
  "canonical_frameworks": {
    "Big_Thing": {
      "path": "frameworks/canonical_Big_Thing.json",
      "strata": "paiab",
      "status": "draft|complete|published",
      "emergent_refs": ["XYZ", "ABC"]
    }
  }
}
```

---

## Next Steps

1. Factor this plan into existing plan doc from before
2. Implement changes in conversation-ingestion MCP:
   - Update Phase 5 tools (create_emergent_framework, preview_emergent)
   - Update Phase 6 tools (finalize_emergent_journey)
   - Implement Phase 7 tools (create_canonical_framework, preview_canonical)
   - Implement Phase 8 tools (render, generate_derivatives, publish)
3. Create metastack templates (EmergentFramework, CanonicalFramework)
4. Test each phase
5. Connect Phase 8 to substrate projector + n8n
