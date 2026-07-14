from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    'AGENTS.md', 'docs/PRODUCT_SPEC.md', 'docs/ACCEPTANCE_MATRIX.md',
    'docs/ARCHITECTURE.md', 'docs/DATA_MODEL.md', 'docs/API_CONTRACT.md',
    'docs/MASTERY_RULES.md', 'docs/AI_GOVERNANCE.md', 'docs/SECURITY.md',
    'docs/TEST_STRATEGY.md', 'docs/RELEASE_PROCESS.md',
    'config/mastery_rules.v1.yaml', 'config/planning_rules.v1.yaml',
    '.github/PULL_REQUEST_TEMPLATE.md'
]

missing = [p for p in REQUIRED if not (ROOT / p).is_file()]
if missing:
    print('Missing governance files:')
    for p in missing:
        print(f' - {p}')
    sys.exit(1)

required_issue_headings = ['## 背景', '## 目标', '## 非目标', '## 验收标准', '## 测试要求', '## 回滚']
errors = []
for issue in sorted((ROOT / 'initial_issues').glob('*.md')):
    if issue.name == 'README.md':
        continue
    text = issue.read_text(encoding='utf-8')
    for heading in required_issue_headings:
        if heading not in text:
            errors.append(f'{issue.relative_to(ROOT)} missing {heading}')

if errors:
    print('Issue contract validation failed:')
    print('\n'.join(f' - {e}' for e in errors))
    sys.exit(1)

print(f'Governance validation passed. Required files: {len(REQUIRED)}, initial issues: {len(list((ROOT / "initial_issues").glob("*.md")))}')
