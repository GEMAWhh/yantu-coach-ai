from pathlib import Path
import re, sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
SKIP_DIRS = {'.git', 'node_modules', '.venv', 'dist', 'coverage', 'references'}
TEXT_EXT = {'.py', '.ts', '.tsx', '.js', '.vue', '.json', '.yml', '.yaml', '.md', '.html', '.env', '.toml'}
patterns = {
    'OpenAI-style secret': re.compile(r'\bsk-[A-Za-z0-9_-]{20,}\b'),
    'Generic API key assignment': re.compile(r'(?i)(api[_-]?key|secret[_-]?key)\s*[:=]\s*["\'][^"\']{12,}["\']'),
    'Hard-coded production data path': re.compile(r'(?i)(data/prod|study\.db).*(fixture|test data)'),
}
findings = []
for path in root.rglob('*'):
    if not path.is_file() or any(part in SKIP_DIRS for part in path.parts):
        continue
    if path.name == 'check_forbidden_patterns.py':
        continue
    if path.suffix.lower() not in TEXT_EXT:
        continue
    try:
        text = path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        continue
    for name, pattern in patterns.items():
        for m in pattern.finditer(text):
            findings.append((path.relative_to(root), name, m.group(0)[:80]))

if findings:
    print('Forbidden or suspicious patterns found:')
    for p, name, excerpt in findings:
        print(f' - {p}: {name}: {excerpt}')
    sys.exit(1)
print('Forbidden-pattern scan passed.')
