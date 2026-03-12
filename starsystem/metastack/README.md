[![Part of STARSYSTEM](https://img.shields.io/badge/Part%20of-STARSYSTEM-blue)](https://github.com/sancovp/starsystem-metarepo)

# Pydantic Stack Core

Typed hierarchical composition for structured text generation through nested Pydantic models.

## Overview

Pydantic Stack Core enables building complex documents through **nested, typed Pydantic models** that render to composite strings via **recursive composition**. The power isn't in simple string concatenation - it's in creating **typed document trees** where each node knows how to render itself and its children.

## The Core Pattern: Nested Typed Composition

Unlike simple templating, this library enables you to:
- Nest typed Pydantic models within other models arbitrarily deep
- Have each model render itself AND its nested children
- Get full type safety and validation at every level
- Build complex documents from reusable, composable pieces

## Installation

[Installation instructions pending PyPI publication]

## Quick Start - Simple Example

```python
from pydantic_stack_core import RenderablePiece, MetaStack, generate_output_from_metastack

# Simple atomic pieces
class Title(RenderablePiece):
    text: str
    level: int = 1
    
    def render(self) -> str:
        return f"{'#' * self.level} {self.text}"

class Paragraph(RenderablePiece):
    content: str
    
    def render(self) -> str:
        return self.content

# Basic usage
stack = MetaStack(pieces=[
    Title(text="Hello", level=1),
    Paragraph(content="World")
])
output = generate_output_from_metastack(stack)
```

## The Real Power: Nested Composition

```python
from pydantic_stack_core import RenderablePiece
from typing import List

# Level 1: Atomic piece
class Author(RenderablePiece):
    name: str
    bio: str
    
    def render(self) -> str:
        return f"**{self.name}** - {self.bio}"

# Level 2: Piece containing other pieces
class CodeExample(RenderablePiece):
    language: str
    code: str
    explanation: str
    
    def render(self) -> str:
        return f"```{self.language}\n{self.code}\n```\n{self.explanation}"

# Level 3: Nested composition with typed fields!
class Section(RenderablePiece):
    title: str
    content: str
    code_examples: List[CodeExample]  # NESTED TYPED MODELS!
    
    def render(self) -> str:
        output = f"## {self.title}\n\n{self.content}\n\n"
        for example in self.code_examples:
            output += example.render() + "\n\n"  # RECURSIVE RENDERING!
        return output

# Level 4: Deep hierarchical document
class BlogPost(RenderablePiece):
    title: str
    author: Author  # NESTED MODEL AS FIELD!
    sections: List[Section]  # LIST OF NESTED MODELS!
    
    def render(self) -> str:
        output = f"# {self.title}\n\n"
        output += self.author.render() + "\n\n"
        for section in self.sections:
            output += section.render()  # CASCADING RENDERS!
        return output

# Build complex document through typed composition
blog = BlogPost(
    title="Understanding Pydantic Stack",
    author=Author(name="Isaac", bio="Building compound intelligence"),
    sections=[
        Section(
            title="Getting Started",
            content="This library enables nested typed composition.",
            code_examples=[
                CodeExample(
                    language="python",
                    code="class MyModel(RenderablePiece):\n    pass",
                    explanation="Define your model by inheriting RenderablePiece"
                )
            ]
        )
    ]
)

# Single render call triggers entire tree!
output = blog.render()
```

This creates a fully typed document tree where:
- **Type safety**: Can't put an Author where a Section belongs
- **Validation**: Pydantic validates at every level
- **Composition**: Sections contain CodeExamples, BlogPosts contain Sections
- **Recursive rendering**: Each piece renders itself and its children

## Advanced Usage

### Custom Separators

```python
# Control spacing between pieces
stack = MetaStack(
    pieces=[...],
    separator="\n\n"  # Double newline between pieces
)
```

### Nested Stacks

Since MetaStack is also a RenderablePiece, you can nest them:

```python
section1 = MetaStack(pieces=[
    Title(text="Section 1", level=2),
    Paragraph(content="Section content...")
])

section2 = MetaStack(pieces=[
    Title(text="Section 2", level=2), 
    Paragraph(content="More content...")
])

document = MetaStack(pieces=[
    Title(text="Main Document", level=1),
    section1,
    section2
])
```

### Custom Rendering Logic

```python
class NumberedList(RenderablePiece):
    items: List[str]
    
    def render(self) -> str:
        return "\n".join(f"{i+1}. {item}" for i, item in enumerate(self.items))

class BulletList(RenderablePiece):
    items: List[str]
    
    def render(self) -> str:
        return "\n".join(f"• {item}" for item in self.items)
```

## Use Cases

- **Documentation Generation**: Create structured docs from data
- **Code Generation**: Build source code from templates  
- **Report Creation**: Compose complex reports from components
- **Template Systems**: Build flexible, reusable content templates
- **Agent Outputs**: Systematic text generation for AI agents

## Integration with HEAVEN Ecosystem

Pydantic Stack Core integrates with:
- **Payload Discovery**: For systematic content generation workflows
- **Powerset Agents**: For structured agent outputs
- **MetaStack Powerset Agent**: For learning and applying stacking patterns

## Development

```bash
# Clone and install for development
git clone https://github.com/sancovp/pydantic-stack-core
cd pydantic-stack-core
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black .
ruff check .
```

## Why Stack-Based?

The stack metaphor makes composition intuitive:
1. **Sequential**: Pieces render in order
2. **Nestable**: Stacks can contain other stacks
3. **Separable**: Control spacing between pieces
4. **Extensible**: Easy to add new piece types

This approach scales from simple text formatting to complex document generation while keeping the API minimal and predictable.

## License

MIT License - see LICENSE file for details.

## Part of HEAVEN Ecosystem

This library is part of the HEAVEN (Hierarchical Event-based Agent-Versatile Environment Network) ecosystem for AI agent development.
