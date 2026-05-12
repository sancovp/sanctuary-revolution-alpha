"""
MAP Poetry System
===================
MAP handles the structural rules (forms, schemes, tones) as homoiconic data.
Python bridges to syllable counting and Claude API for actual generation.
The hot-reload engine means you can rewrite poetic forms mid-session.
"""

import os
import sys
import json
import re
import subprocess
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from base.eval import run as map_run
from base.types import Atom, Cell, NIL, MAPObj

# ── MAP env ──────────────────────────────────────────────────────────────

def boot_poetry_env():
    """Boot a MAP env with the poetry op loaded."""
    env = None
    poetry_src = open(os.path.join(os.path.dirname(__file__), 'super/ops/poetry.map')).read()
    # Strip comment lines so the evaluator doesn't choke
    lines = [l for l in poetry_src.split('\n') if not l.strip().startswith('#')]
    src = '\n'.join(lines)
    # Run each top-level form
    for expr in split_top_level(src):
        expr = expr.strip()
        if expr:
            try:
                _, env = map_run(expr, env)
            except Exception as e:
                print(f"[map boot warning] {expr[:60]!r}: {e}")
    return env

def split_top_level(src):
    """Split source into top-level {…} forms."""
    forms, depth, start = [], 0, 0
    for i, ch in enumerate(src):
        if ch == '{':
            if depth == 0: start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                forms.append(src[start:i+1])
    return forms

def map_query(expr, env):
    """Run a MAP expression and return (result_str, new_env)."""
    result, env = map_run(expr, env)
    return str(result), env

def map_list_to_python(obj):
    """Convert a MAP Cell list to a Python list of strings."""
    items = []
    while isinstance(obj, Cell):
        items.append(str(obj.head))
        obj = obj.tail
    return items

# ── Syllable counting ───────────────────────────────────────────────────────

def count_syllables(word):
    """Rough English syllable counter."""
    word = word.lower().strip(".,!?;:\"'")
    if not word:
        return 0
    # Count vowel groups
    vowels = re.findall(r'[aeiouy]+', word)
    count = len(vowels)
    # Adjust for silent e
    if word.endswith('e') and count > 1:
        count -= 1
    # Adjust for common patterns
    if word.endswith('le') and len(word) > 2 and word[-3] not in 'aeiou':
        count += 1
    return max(1, count)

def count_line_syllables(line):
    return sum(count_syllables(w) for w in line.split())

def analyze_poem(poem_text):
    """Return syllable count per line."""
    lines = [l for l in poem_text.strip().split('\n') if l.strip()]
    return [(line, count_line_syllables(line)) for line in lines]

# ── Claude API ──────────────────────────────────────────────────────────────

def call_claude(system_prompt, user_prompt, max_tokens=600):
    """Call Claude API directly."""
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        return "[no ANTHROPIC_API_KEY set]"

    payload = json.dumps({
        "model": "claude-sonnet-4-6",
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}]
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
            return data['content'][0]['text']
    except urllib.error.HTTPError as e:
        return f"[API error {e.code}: {e.read().decode()}]"

# ── Poetry generation ────────────────────────────────────────────────────────

FORM_DESCRIPTIONS = {
    ':HAIKU':   ('haiku', '3 lines: 5-7-5 syllables', 'AABB'),
    ':TANKA':   ('tanka', '5 lines: 5-7-5-7-7 syllables', 'free'),
    ':COUPLET': ('couplet', '2 lines of 10 syllables each', 'AA'),
}

SCHEME_DESCRIPTIONS = {
    ':AABB': 'couplet rhyme (AABB)',
    ':ABAB': 'alternating rhyme (ABAB)',
    ':ABBA': 'envelope rhyme (ABBA)',
    ':FREE': 'free verse (no rhyme)',
}

def generate_poem(subject, form=':HAIKU', scheme=':FREE', tone=':WONDER', env=None):
    """Use MAP to get structural constraints, then generate with Claude."""

    # Ask MAP for form description
    try:
        form_desc, env = map_query(f'{{describe-form {form}}}', env)
        tones_raw, env = map_query(f'{{get-tone {tone}}}', env)
    except Exception as e:
        form_desc = "unknown"
        tones_raw = ""

    # Parse tone keywords
    tone_words = [t.strip(':').lower() for t in tones_raw.split() if t.startswith(':')]
    tone_str = ', '.join(tone_words) if tone_words else 'neutral'

    form_name, form_hint, _ = FORM_DESCRIPTIONS.get(form, ('poem', 'a poem', 'free'))
    scheme_hint = SCHEME_DESCRIPTIONS.get(scheme, 'free verse')

    syllable_rules = {
        ':HAIKU':   'Line 1: exactly 5 syllables. Line 2: exactly 7 syllables. Line 3: exactly 5 syllables.',
        ':TANKA':   'Line 1: 5. Line 2: 7. Line 3: 5. Line 4: 7. Line 5: 7.',
        ':COUPLET': 'Two lines, each with 10 syllables (iambic pentameter encouraged).',
    }.get(form, 'No specific syllable constraints.')

    system = (
        f"You are a poet's assistant. Write a single {form_name} with absolute precision. "
        f"Return ONLY the poem — no title, no explanation, no punctuation notes. "
        f"Tone: {tone_str}."
    )

    user = (
        f"Write a {form_name} about: {subject}\n\n"
        f"Structural rules (from MAP engine): {form_desc}\n"
        f"{syllable_rules}\n"
        f"Rhyme scheme: {scheme_hint}\n"
        f"Tone words to draw from: {tone_str}\n\n"
        f"Return only the poem lines, nothing else."
    )

    poem = call_claude(system, user)

    # Analyze syllables
    analysis = analyze_poem(poem)

    return poem, analysis, env

def revise_poem(poem, feedback, form=':HAIKU', env=None):
    """Revise a poem based on feedback, keeping structural rules from Map."""
    form_name, form_hint, _ = FORM_DESCRIPTIONS.get(form, ('poem', 'a poem', 'free'))
    syllable_rules = {
        ':HAIKU':   '5-7-5 syllables across 3 lines',
        ':TANKA':   '5-7-5-7-7 syllables across 5 lines',
        ':COUPLET': '10-10 syllables across 2 lines',
    }.get(form, 'maintain the original structure')

    system = "You are a poet's assistant. Revise the poem as requested. Return ONLY the revised poem."
    user = (
        f"Original {form_name}:\n{poem}\n\n"
        f"Revision request: {feedback}\n"
        f"Keep the form ({syllable_rules}). Return only the poem."
    )
    revised = call_claude(system, user)
    analysis = analyze_poem(revised)
    return revised, analysis, env

# ── REPL ─────────────────────────────────────────────────────────────────────

def print_analysis(analysis):
    for line, count in analysis:
        marker = '✓' if count else '?'
        print(f"  {marker} ({count:2d} syl) {line}")

def repl():
    print("\n╔══════════════════════════════════════════╗")
    print("║       MAP POETRY SYSTEM  v1.0         ║")
    print("║  Structural rules: MAP homoiconic data ║")
    print("║  Generation: Claude API                  ║")
    print("╚══════════════════════════════════════════╝\n")

    print("[*] Booting MAP environment...")
    env = boot_poetry_env()
    print("[✓] MAP poetry ops loaded\n")

    state = {
        'form': ':HAIKU',
        'scheme': ':FREE',
        'tone': ':WONDER',
        'last_poem': None,
    }

    def show_state():
        print(f"  Form: {state['form']}  Scheme: {state['scheme']}  Tone: {state['tone']}")

    def show_help():
        print("""
Commands:
  write <subject>          Generate a poem about subject
  revise <feedback>        Revise the last poem
  form <HAIKU|TANKA|COUPLET>   Set poetic form
  scheme <AABB|ABAB|ABBA|FREE> Set rhyme scheme
  tone <MELANCHOLY|WONDER|FIERCE|TENDER>  Set tone
  map <expr>             Run a raw MAP expression
  state                    Show current settings
  help                     This message
  quit                     Exit
""")

    show_help()
    show_state()

    current_poem = None

    while True:
        try:
            raw = input("\npoetry> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[bye]")
            break

        if not raw:
            continue

        cmd, _, rest = raw.partition(' ')
        cmd = cmd.lower()

        if cmd in ('quit', 'exit', 'q'):
            print("[bye]")
            break

        elif cmd == 'help':
            show_help()

        elif cmd == 'state':
            show_state()

        elif cmd == 'form':
            val = rest.strip().upper()
            key = f':{val}'
            if key in FORM_DESCRIPTIONS:
                state['form'] = key
                print(f"[✓] Form set to {key}")
            else:
                print(f"Unknown form. Try: HAIKU, TANKA, COUPLET")

        elif cmd == 'scheme':
            val = rest.strip().upper()
            key = f':{val}'
            if key in SCHEME_DESCRIPTIONS:
                state['scheme'] = key
                print(f"[✓] Scheme set to {key}")
            else:
                print(f"Unknown scheme. Try: AABB, ABAB, ABBA, FREE")

        elif cmd == 'tone':
            val = rest.strip().upper()
            key = f':{val}'
            tones = [':MELANCHOLY', ':WONDER', ':FIERCE', ':TENDER']
            if key in tones:
                state['tone'] = key
                print(f"[✓] Tone set to {key}")
            else:
                print(f"Unknown tone. Try: MELANCHOLY, WONDER, FIERCE, TENDER")

        elif cmd == 'write':
            if not rest:
                print("Usage: write <subject>")
                continue
            print(f"\n[Map] Querying structural constraints for {state['form']}...")
            print(f"[Claude] Generating {state['form']} about '{rest}'...\n")
            poem, analysis, env = generate_poem(rest, state['form'], state['scheme'], state['tone'], env)
            current_poem = poem
            print("─" * 40)
            print(poem)
            print("─" * 40)
            print("\n[Syllable analysis]")
            print_analysis(analysis)

        elif cmd == 'revise':
            if not current_poem:
                print("No poem yet. Use 'write' first.")
                continue
            if not rest:
                print("Usage: revise <feedback>")
                continue
            print(f"\n[Claude] Revising...\n")
            poem, analysis, env = revise_poem(current_poem, rest, state['form'], env)
            current_poem = poem
            print("─" * 40)
            print(poem)
            print("─" * 40)
            print("\n[Syllable analysis]")
            print_analysis(analysis)

        elif cmd == 'map':
            if not rest:
                print("Usage: map <expr>")
                continue
            try:
                result, env = map_query(rest, env)
                print(f"=> {result}")
            except Exception as e:
                print(f"[map error] {e}")

        else:
            print(f"Unknown command '{cmd}'. Type 'help'.")

if __name__ == '__main__':
    repl()
