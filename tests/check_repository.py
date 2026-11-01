"""Validate links, syntax, skill metadata and the publication allowlist."""
import ast
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
errors = []
for path in ROOT.rglob('*'):
    rel = path.relative_to(ROOT)
    if '.git' in rel.parts or '__pycache__' in rel.parts or not path.is_file():
        continue
    if path.suffix.lower() not in {'.md', '.py', '.ps1', '.html', '.js', '.css', '.png', '.jpg'} and path.name not in {'.gitignore', 'LICENSE'}:
        errors.append(f'Unexpected publication file: {rel}')
        continue
    if path.suffix.lower() in {'.png', '.jpg'}:
        if rel.parts[:2] != ('docs', 'images'):
            errors.append(f'Image outside docs/images: {rel}')
        continue
    text = path.read_text(encoding='utf-8')
    if path.suffix == '.py':
        ast.parse(text, filename=str(rel))
    if path.suffix == '.md':
        for target in re.findall(r'\]\(([^)]+)\)', text):
            if '://' not in target and not target.startswith('#'):
                if not (path.parent / target.split('#', 1)[0]).resolve().exists():
                    errors.append(f'Broken link in {rel}: {target}')
    personal_path = re.search(r'[A-Za-z]:[\\/]+Users[\\/]+[^<>\s\\/]+', text)
    if personal_path:
        errors.append(f'Personal absolute path in {rel}')
    # Construct patterns so the checker does not flag its own definitions.
    patterns = [r'gh' + r'[pousr]_[A-Za-z0-9]{25,}', r'github_' + r'pat_[A-Za-z0-9_]{25,}', r'sk-' + r'[A-Za-z0-9_-]{25,}']
    if any(re.search(pattern, text) for pattern in patterns):
        errors.append(f'Possible credential in {rel}')
    if path.stat().st_size > 500_000:
        errors.append(f'Unexpected large source file: {rel}')
skill = ROOT / 'jarvis/skills/jarvis-workspace/SKILL.md'
content = skill.read_text(encoding='utf-8')
if not content.startswith('---\nname: jarvis-workspace\n'):
    errors.append('Invalid skill metadata')
if errors:
    raise SystemExit('\n'.join(errors))
print('Publication file scope, links, Python syntax, credential patterns and skill metadata passed.')
