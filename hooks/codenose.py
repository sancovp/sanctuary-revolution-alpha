#!/usr/bin/env python3
# codenose ignore
"""
The CodeNose 👃 - Detects code smells for LLMs
Sniffs out duplicate logic, missing logging, architecture violations, and other LLM blind spots
"""
import json
import sys
import re
import ast
import py_compile
import tempfile
import os
from collections import defaultdict
from pathlib import Path

# =============================================================================
# CONFIGURATION
# =============================================================================

ARCH_LOCK_FILE = os.path.expanduser("~/.claude/.codenose_arch_lock")

# Canonical filenames per the meta² architecture
CANONICAL_FILENAMES = {
    "__init__.py",
    "utils.py",
    "core.py",
    "models.py",
    "mcp_server.py",
    "api.py",
    "cli.py",
    "main.py",
    "config.py",
    "constants.py",
    "types.py",
    "exceptions.py",
}

# Directories that can have any Python files
EXEMPT_DIRS = {"util_deps", "tests", "test", "__pycache__", "migrations"}

# Test file patterns
TEST_PATTERNS = [r"^test_.*\.py$", r"^.*_test\.py$", r"^conftest\.py$"]

# Smell emoji legend
SMELL_LEGEND = {
    "syntax": "🔴",      # Critical - syntax error
    "syspath": "💀",     # Critical - sys.path manipulation
    "traceback": "☠️",   # Critical - missing traceback
    "arch": "🏗️",        # Architecture violation
    "facade": "🧅",      # Logic in facade (onion violation)
    "dup": "👯",         # Duplication
    "long": "📏",        # Long function
    "log": "📝",         # Missing logging
    "import": "📦",      # Import duplication
}

CRITICAL_SMELLS = {"syntax", "syspath", "traceback"}


# =============================================================================
# SMELL DETECTORS - Return structured data, not strings
# =============================================================================

def check_syntax_errors(content, file_path):
    """Check for Python syntax errors"""
    if not file_path.endswith('.py'):
        return []

    try:
        ast.parse(content)
        return []
    except SyntaxError as e:
        return [{"type": "syntax", "line": e.lineno, "msg": e.msg, "critical": True}]
    except Exception as e:
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(content)
                temp_file = f.name
            py_compile.compile(temp_file, doraise=True)
            os.unlink(temp_file)
            return []
        except py_compile.PyCompileError as e:
            os.unlink(temp_file)
            return [{"type": "syntax", "line": 0, "msg": str(e), "critical": True}]
        except Exception:
            if 'temp_file' in locals():
                os.unlink(temp_file)
            return [{"type": "syntax", "line": 0, "msg": f"Parse failed: {e}", "critical": True}]


def check_duplication(content, file_path):
    """Check for duplicate logic blocks"""
    lines = content.split('\n')
    min_lines = 3
    meaningful_blocks = []

    for i in range(len(lines) - min_lines + 1):
        block_lines = []
        for j in range(min_lines):
            line = lines[i + j].strip()
            if (line and
                not line.startswith('#') and
                not line.startswith('"""') and
                not line.startswith("'''") and
                len(line) > 10 and
                ('=' in line or 'if ' in line or 'for ' in line or 'while ' in line or 'def ' in line)):
                block_lines.append(line)

        if len(block_lines) >= min_lines:
            block_text = '\n'.join(block_lines)
            meaningful_blocks.append((block_text, i + 1))

    block_counts = defaultdict(list)
    for block_text, line_num in meaningful_blocks:
        normalized = re.sub(r'\s+', ' ', block_text.strip())
        if len(normalized) > 30:
            block_counts[normalized].append(line_num)

    smells = []
    for block_text, line_numbers in block_counts.items():
        if len(line_numbers) > 1:
            smells.append({
                "type": "dup",
                "lines": line_numbers,
                "count": len(line_numbers),
                "critical": False
            })
    return smells


def check_logging(content, file_path):
    """Check if code uses proper logging"""
    if 'test' in file_path.lower() or len(content.split('\n')) < 20:
        return []

    has_functions = 'def ' in content
    has_error_handling = 'except' in content or 'raise' in content
    has_external_calls = any(keyword in content for keyword in ['requests.', 'open(', 'subprocess.'])

    should_have_logging = has_functions and (has_error_handling or has_external_calls or len(content.split('\n')) > 50)

    if should_have_logging and 'logging.' not in content and 'logger.' not in content:
        return [{"type": "log", "line": 0, "msg": "No logging found", "critical": False}]
    return []


def check_modularization(content, file_path):
    """Check if functions are too long"""
    smells = []
    lines = content.split('\n')
    current_function = None
    function_start = 0
    indent_level = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('def '):
            if current_function and (i - function_start) > 33:
                smells.append({
                    "type": "long",
                    "line": function_start + 1,
                    "msg": f"{current_function}() is {i - function_start} lines",
                    "critical": False
                })
            current_function = stripped.split('(')[0].replace('def ', '')
            function_start = i
            indent_level = len(line) - len(line.lstrip())
        elif current_function and line.strip() and len(line) - len(line.lstrip()) <= indent_level and stripped != '':
            if (i - function_start) > 33:
                smells.append({
                    "type": "long",
                    "line": function_start + 1,
                    "msg": f"{current_function}() is {i - function_start} lines",
                    "critical": False
                })
            current_function = None
    return smells


def check_import_duplication(content, file_path):
    """Check for imports that appear both globally and locally"""
    lines = content.split('\n')
    global_imports = set()
    local_imports = []
    in_function = False

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('def ') or stripped.startswith('class '):
            in_function = True
        elif line and not line[0].isspace() and not stripped.startswith(('#', '"""', "'''")):
            in_function = False

        if stripped.startswith(('import ', 'from ')):
            if stripped.startswith('import '):
                module = stripped.replace('import ', '').split(' as ')[0].split('.')[0].split(',')[0].strip()
            elif stripped.startswith('from '):
                module = stripped.split(' ')[1].split('.')[0].strip()
            else:
                continue
            if not in_function:
                global_imports.add(module)
            else:
                local_imports.append((module, i + 1))

    smells = []
    for module, line_num in local_imports:
        if module in global_imports:
            smells.append({
                "type": "import",
                "line": line_num,
                "msg": f"'{module}' duplicated globally and locally",
                "critical": False
            })
    return smells


def check_sys_path_usage(content, file_path):
    """Check for forbidden sys.path manipulation"""
    smells = []
    lines = content.split('\n')

    for i, line in enumerate(lines):
        stripped = line.strip().lower()
        if 'sys.path' in stripped and not stripped.startswith('#'):
            smells.append({
                "type": "syspath",
                "line": i + 1,
                "msg": "sys.path manipulation",
                "critical": True
            })
        if ('pythonpath' in stripped and
            ('subprocess' in stripped or 'os.' in stripped or 'bash' in stripped) and
            not stripped.startswith('#')):
            smells.append({
                "type": "syspath",
                "line": i + 1,
                "msg": "PYTHONPATH manipulation",
                "critical": True
            })
    return smells


def check_traceback_handling(content, file_path):
    """Check for exception handling without proper traceback logging"""
    smells = []
    lines = content.split('\n')
    in_except_block = False
    except_line = 0
    block_content = []

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('except'):
            in_except_block = True
            except_line = i + 1
            block_content = []
        elif in_except_block:
            if line.strip() == '' or line.startswith('    ') or line.startswith('\t'):
                block_content.append(stripped)
            else:
                block_text = ' '.join(block_content).lower()
                has_traceback = any(keyword in block_text for keyword in [
                    'traceback', 'exc_info', 'logging.exception', 'logger.exception',
                    'print_exc', 'format_exc', 'tb_', 'raise', 're-raise'
                ])
                has_substance = any(keyword in block_text for keyword in [
                    'return', 'print(', 'logging.', 'logger.', '=', 'if ', 'for ', 'while '
                ]) and 'pass' not in block_text

                if has_substance and not has_traceback:
                    smells.append({
                        "type": "traceback",
                        "line": except_line,
                        "msg": "Exception without traceback",
                        "critical": True
                    })
                in_except_block = False
    return smells


def check_architecture(file_path):
    """Check if file follows canonical architecture naming"""
    path = Path(file_path)
    filename = path.name
    parent_dir = path.parent.name
    path_parts = set(path.parts)

    # Skip non-Python files
    if not filename.endswith('.py'):
        return []

    # Skip exempt directories (check path components, not substrings)
    if parent_dir in EXEMPT_DIRS or any(d in path_parts for d in EXEMPT_DIRS):
        return []

    # Skip test files
    for pattern in TEST_PATTERNS:
        if re.match(pattern, filename):
            return []

    # Check if filename is canonical
    if filename not in CANONICAL_FILENAMES:
        return [{
            "type": "arch",
            "line": 0,
            "msg": f"'{filename}' is not canonical. Use: utils.py, core.py, models.py, mcp_server.py, api.py, cli.py",
            "critical": False,
            "filename": filename
        }]
    return []


def check_facade_logic(content, file_path):
    """Check if facade files (mcp_server.py, api.py, cli.py) contain logic instead of pure delegation"""
    path = Path(file_path)
    filename = path.name

    # Only check facade files
    facade_files = {"mcp_server.py", "api.py", "cli.py"}
    if filename not in facade_files:
        return []

    smells = []
    lines = content.split('\n')

    # Logic indicators that shouldn't be in facades
    logic_patterns = [
        (r'\bif\s+.*:', 'conditional logic'),
        (r'\bfor\s+.*:', 'loop'),
        (r'\bwhile\s+.*:', 'loop'),
        (r'\btry\s*:', 'try/except block'),
        (r'^\s+\w+\s*=\s*(?!.*\b(core|utils)\b)', 'assignment/computation'),
    ]

    # Skip patterns (these are OK in facades)
    skip_patterns = [
        r'^\s*#',           # comments
        r'^\s*$',           # empty lines
        r'@\w+',            # decorators
        r'def\s+\w+',       # function definitions
        r'return\s+',       # returns (delegation)
        r'from\s+',         # imports
        r'import\s+',       # imports
        r'class\s+',        # class definitions
        r'"""',             # docstrings
        r"'''",             # docstrings
    ]

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Skip obvious non-logic lines
        if any(re.match(p, stripped) for p in skip_patterns):
            continue

        # Check for logic patterns
        for pattern, logic_type in logic_patterns:
            if re.search(pattern, line) and 'return' not in line:
                # Extra check: is this inside a function that just delegates?
                smells.append({
                    "type": "facade",
                    "line": i + 1,
                    "msg": f"Logic in facade: {logic_type}",
                    "critical": False
                })
                break  # One smell per line max

    # Only report if there's substantial logic (>2 instances)
    if len(smells) > 2:
        return smells[:3]  # Limit output
    return []


# =============================================================================
# OUTPUT FORMATTING
# =============================================================================

def is_arch_locked():
    """Check if architecture lock mode is enabled"""
    return os.path.exists(ARCH_LOCK_FILE)


def format_compressed_output(smells, file_path):
    """Format smells as compressed <codenose> output"""
    if not smells:
        return None

    # Count by type
    by_type = defaultdict(list)
    for smell in smells:
        by_type[smell["type"]].append(smell)

    # Check for critical
    has_critical = any(s.get("critical") for s in smells)

    # Build legend (only show present smell types)
    legend_parts = []
    for smell_type in by_type:
        emoji = SMELL_LEGEND.get(smell_type, "👃")
        legend_parts.append(f"{emoji}={smell_type}")
    legend = " | ".join(legend_parts)

    # Build table
    table_lines = ["| Smell | Location | Info |", "|-------|----------|------|"]
    for smell_type, type_smells in by_type.items():
        emoji = SMELL_LEGEND.get(smell_type, "👃")
        for smell in type_smells[:3]:  # Limit to 3 per type
            line = smell.get("line", 0)
            loc = f"L{line}" if line else "file"
            msg = smell.get("msg", "")[:40]
            table_lines.append(f"| {emoji} | {loc} | {msg} |")
        if len(type_smells) > 3:
            table_lines.append(f"| {emoji} | ... | +{len(type_smells) - 3} more |")

    # Build output
    critical_str = "🚨 CRITICAL" if has_critical else ""
    lock_str = "[ARCH LOCK: ON]" if is_arch_locked() else ""

    output = f"""<codenose>
{len(smells)} smell(s) {critical_str} {lock_str}
{legend}

{chr(10).join(table_lines)}
</codenose>"""

    return output


# =============================================================================
# MAIN HOOK LOGIC
# =============================================================================

try:
    input_data = json.load(sys.stdin)
    tool_name = input_data.get("tool_name", "unknown")
    tool_input = input_data.get("tool_input", {})

    if tool_name in ["Edit", "Write", "MultiEdit"]:
        file_path = tool_input.get("file_path", "")

        if file_path.endswith(('.py', '.js', '.ts', '.java', '.cpp', '.c')):
            try:
                with open(file_path, 'r') as f:
                    content = f.read()

                # Skip if file has codenose ignore directive
                if '# codenose ignore' in content or '// codenose ignore' in content:
                    sys.exit(0)

                all_smells = []

                # Check architecture first (can block in lock mode)
                arch_smells = check_architecture(file_path)
                if arch_smells and is_arch_locked():
                    # In lock mode, architecture violations are critical and block
                    for smell in arch_smells:
                        smell["critical"] = True
                    output = format_compressed_output(arch_smells, file_path)
                    print(output, file=sys.stderr)
                    print(f"\n🔒 ARCH LOCK MODE: Cannot write non-canonical file '{Path(file_path).name}'", file=sys.stderr)
                    sys.exit(1)  # Block the write

                all_smells.extend(arch_smells)

                # Check syntax first
                syntax_smells = check_syntax_errors(content, file_path)
                if syntax_smells:
                    all_smells.extend(syntax_smells)
                else:
                    # Only run other checks if syntax is valid
                    all_smells.extend(check_duplication(content, file_path))
                    all_smells.extend(check_logging(content, file_path))
                    all_smells.extend(check_modularization(content, file_path))
                    all_smells.extend(check_import_duplication(content, file_path))
                    all_smells.extend(check_sys_path_usage(content, file_path))
                    all_smells.extend(check_traceback_handling(content, file_path))
                    all_smells.extend(check_facade_logic(content, file_path))

                # Only output if there are critical smells (hide non-critical by default)
                has_critical = any(s.get("critical") for s in all_smells)

                if has_critical:
                    output = format_compressed_output(all_smells, file_path)
                    if output:
                        print(output, file=sys.stderr)
                        sys.exit(2)

            except Exception as e:
                print(f"👃 CodeNose error: {e}", file=sys.stderr)

    sys.exit(0)

except Exception as e:
    print(f"👃 CodeNose malfunction: {e}", file=sys.stderr)
    sys.exit(1)
