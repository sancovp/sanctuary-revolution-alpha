"""
Pydantic Stack Core - Typed hierarchical composition for structured text generation.

This library enables building complex documents through nested, typed Pydantic models
that render to composite strings through recursive composition.

Core Pattern: NESTED TYPED COMPOSITION
=======================================
The power isn't in concatenating strings - it's in building typed document trees
where each node knows how to render itself and its children.

Key Components:
1. RenderablePiece - Base class that enables nesting typed models within each other
2. MetaStack - Top-level container for any RenderablePiece models
3. FractalPattern - Generic template for recursive patterns (AIDA, Hero's Journey, etc.)
4. MetaStackRenderer MCP - Agent-accessible template system via Model Context Protocol

The Real Power: HIERARCHICAL COMPOSITION
=========================================
RenderablePiece models can contain other RenderablePiece models as typed fields,
creating arbitrarily deep document structures with full type safety and validation.

LLM WORKFLOW - Using MetaStack via MCP
=======================================
The MetaStackRenderer MCP enables AI agents to create, register, and use templates
through a simple 3-step workflow:

**Step 1: Create Template Classes (in sandbox filesystem)**
    ```python
    # Write to /tmp/my_templates.py or any .py file
    from pydantic_stack_core import RenderablePiece, MetaStack
    from typing import List

    class BlogPost(MetaStack):
        title: str
        author: str
        sections: List[str]

        def render(self) -> str:
            output = f"# {self.title}\\n\\nBy: {self.author}\\n\\n"
            for section in self.sections:
                output += f"{section}\\n\\n"
            return output
    ```

**Step 2: Register Template via MCP**
    ```python
    # Use the metastack MCP tool
    mcp__metastack__register_metastack(
        name="blog_post",
        class_path="my_templates.BlogPost",  # module.ClassName
        domain="content_creation",
        subdomain="blog_posts",
        process="drafting",
        tags=["marketing", "technical"],
        defaults={"author": "Isaac"},
        description="Blog post template for technical content"
    )
    ```

**Step 3: Render Templates via MCP**
    ```python
    # Render in memory
    output = mcp__metastack__render_metastack(
        metastack_name="blog_post",
        content={
            "title": "My Post",
            "sections": ["Introduction...", "Main content..."]
        }
    )

    # Or render to file
    mcp__metastack__render_to_file(
        metastack_name="blog_post",
        content={"title": "My Post", "sections": [...]},
        file_path="/tmp/output.md"
    )
    ```

**Available MCP Tools:**
- `list_metastacks()` - See all registered templates
- `describe_metastack(name)` - Get template metadata
- `register_metastack(...)` - Add new template to registry
- `render_metastack(name, content)` - Render in memory
- `render_to_file(name, content, path)` - Render to file
- `append_from(source, content, target)` - Compose templates
- `get_help(topic)` - Get Python help for classes

BUILT-IN TEMPLATES
==================
**FractalPattern** - Generic recursive pattern template:
    ```python
    from pydantic_stack_core import FractalStage, FractalPattern

    # Create stages
    stage = FractalStage(
        emoji="🧲",
        name="Lead Magnet",
        substages={
            "Attention": "Free value offering",
            "Interest": "Content quality piques interest",
            "Desire": "Recognition of additional needs",
            "Action": "Opt-in or registration"
        },
        transformation_from="Visitor",
        transformation_to="Engaged Lead"
    )

    # Build pattern
    pattern = FractalPattern(
        pattern_name="AIDA Value Ladder",
        pattern_description="Customer journey with AIDA cycles",
        stages=[stage1, stage2, ...],
        meta_insight="Leverages ADHD trigger cycles...",
        failure_strategies={"Lead Magnet": ["Retarget", "A/B test"]},
        feedback_loops={"Lead Magnet": ("Survey", "Understand impression")},
        storytelling={"Lead Magnet": ("Success story", "Inspire hope")}
    )

    output = pattern.render()  # Full recursive pattern visualization
    ```

MANUAL CODE USAGE (Without MCP)
================================
Example - Nested Typed Composition:
    ```python
    from pydantic_stack_core import RenderablePiece, MetaStack
    from typing import List

    # Level 1: Atomic piece
    class Author(RenderablePiece):
        name: str
        bio: str

        def render(self) -> str:
            return f"**{self.name}** - {self.bio}"

    # Level 2: Piece containing pieces
    class Section(RenderablePiece):
        title: str
        content: str
        code_examples: List['CodeExample']  # NESTED TYPED MODELS!

        def render(self) -> str:
            output = f"## {self.title}\\n{self.content}\\n"
            for example in self.code_examples:
                output += example.render()  # RECURSIVE RENDERING!
            return output

    # Level 3: Deep nesting
    class BlogPost(RenderablePiece):
        title: str
        author: Author  # NESTED TYPED MODEL!
        sections: List[Section]  # NESTED LIST OF TYPED MODELS!

        def render(self) -> str:
            output = f"# {self.title}\\n\\n"
            output += self.author.render() + "\\n\\n"
            for section in self.sections:
                output += section.render()  # CASCADE OF RENDERS!
            return output

    # Build complex document through typed composition
    post = BlogPost(
        title="My Post",
        author=Author(name="Isaac", bio="AI Developer"),
        sections=[Section(...), Section(...)]
    )

    # Triggers recursive rendering through entire tree
    output = post.render()
    ```

Benefits:
- Type Safety: Can't put wrong types in wrong places
- Validation: Pydantic validates at every nesting level
- Composition: Build complex from simple, reuse components
- Discoverability: IDE shows exactly what goes where
- Agent-Accessible: MCP integration for AI workflows
- Template Registry: Reusable templates with metadata
"""

from .core import RenderablePiece, MetaStack, generate_output_from_metastack
from .fractal import FractalStage, FractalPattern

__version__ = "0.1.0"
__all__ = [
    "RenderablePiece",
    "MetaStack",
    "generate_output_from_metastack",
    "FractalStage",
    "FractalPattern",
]