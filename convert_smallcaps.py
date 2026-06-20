"""
Safer small caps converter — only targets non-f-string literals.
"""
import re
import os

SMALL_CAPS_MAP = {
    'A': 'ᴀ', 'B': 'ʙ', 'C': 'ᴄ', 'D': 'ᴅ', 'E': 'ᴇ',
    'F': 'ғ', 'G': 'ɢ', 'H': 'ʜ', 'I': 'ɪ', 'J': 'ᴊ',
    'K': 'ᴋ', 'L': 'ʟ', 'M': 'ᴍ', 'N': 'ɴ', 'O': 'ᴏ',
    'P': 'ᴘ', 'Q': 'ǫ', 'R': 'ʀ', 'S': 's', 'T': 'ᴛ',
    'U': 'ᴜ', 'V': 'ᴠ', 'W': 'ᴡ', 'X': 'х', 'Y': 'ʏ',
    'Z': 'ᴢ',
    'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ',
    'f': 'ғ', 'g': 'ɢ', 'h': 'ʜ', 'i': 'ɪ', 'j': 'ᴊ',
    'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ', 'o': 'ᴏ',
    'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ', 's': 's', 't': 'ᴛ',
    'u': 'ᴜ', 'v': 'ᴠ', 'w': 'ᴡ', 'x': 'х', 'y': 'ʏ',
    'z': 'ᴢ',
}

HTML_TAG_RE = re.compile(r'<[^>]+>')
FORMAT_PLACEHOLDER_RE = re.compile(r'\{[^}]*\}')
URL_RE = re.compile(r'https?://\S+')
CODE_BLOCK_RE = re.compile(r'<code>.*?</code>')


def to_small_caps(text):
    return "".join(SMALL_CAPS_MAP.get(ch, ch) for ch in text)


def should_skip_string(s):
    stripped = s.strip()
    if not stripped:
        return True
    if stripped.isdigit():
        return True
    if re.match(r'^[a-z_][a-z0-9_]*$', stripped):
        return True
    if re.match(r'^\{[^}]*\}$', stripped):
        return True
    return False


def convert_display_text(text):
    """Convert display text to small caps, preserving protected regions."""
    # Collect all protected spans (HTML, format, URLs, code)
    protected = []
    for pattern in (HTML_TAG_RE, FORMAT_PLACEHOLDER_RE, URL_RE, CODE_BLOCK_RE):
        for m in pattern.finditer(text):
            protected.append((m.start(), m.end()))
    # Sort and merge
    protected.sort()
    merged = []
    for start, end in protected:
        if merged and start < merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    # Build output: convert unprotected parts
    parts = []
    last_end = 0
    for start, end in merged:
        if start > last_end:
            parts.append(to_small_caps(text[last_end:start]))
        parts.append(text[start:end])
        last_end = end
    if last_end < len(text):
        parts.append(to_small_caps(text[last_end:]))
    return "".join(parts)


def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    modified = False

    # Pattern for non-f-string double-quoted strings
    # Matches: "text" but NOT f"text"
    for pattern_data in [
        (r'"""[\s\S]*?"""', False),   # triple double, multiline
        (r"\'\'\'[\s\S]*?\'\'\'", False),  # triple single, multiline
        (r'(?<!f)(?<!F)"[^"]*"', False),   # double-quoted, not f-string
    ]:
        pattern, is_fstring = pattern_data
        matches = list(re.finditer(pattern, content))
        for m in reversed(matches):
            orig = m.group(0)
            inner = orig[1:-1]  # strip quotes
            if should_skip_string(inner):
                continue
            converted = convert_display_text(inner)
            if converted != inner:
                new_str = orig[0] + converted + orig[-1]
                content = content[:m.start()] + new_str + content[m.end():]
                modified = True

    # Single-quoted strings - be careful not to corrupt inside f-string expressions
    # Strategy: find single-quoted strings NOT inside braces
    # We use a simpler approach: process the whole file char by char
    # to find strings that are in display context
    for m in reversed(list(re.finditer(r"'[^']*'", content))):
        # Check context: is this inside {} (f-string expression)?
        pos = m.start()
        before = content[:pos]
        # Count unescaped { and } before this position
        brace_depth = before.count('{') - before.count('}')
        if brace_depth > 0:
            continue  # inside f-string expression, skip
        orig = m.group(0)
        inner = orig[1:-1]
        if should_skip_string(inner):
            continue
        converted = convert_display_text(inner)
        if converted != inner:
            new_str = "'" + converted + "'"
            content = content[:m.start()] + new_str + content[m.end():]
            modified = True

    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False


if __name__ == "__main__":
    targets = [
        "bot.py", "utils.py", "purchase.py", "subscription.py",
        "broadcast.py", "content_manager.py", "login_manager.py",
    ]
    for fname in targets:
        if os.path.exists(fname):
            changed = process_file(fname)
            print(f"{'MODIFIED' if changed else 'SKIPPED'}: {fname}")
