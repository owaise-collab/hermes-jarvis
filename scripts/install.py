"""Install local routing, a vault map, a Hermes skill and a launcher, with rollback."""
import argparse
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'jarvis'))
from core import LocalModel, Vault, atomic_write

MARKER = '## Jarvis local workspace'


def local_settings(config, endpoint, model):
    LocalModel(endpoint, model)  # Validate before touching configuration.
    config.setdefault('model', {}).update(default=model, provider='llamacpp', base_url=endpoint,
        api_key='local-only', context_length=65536)
    config.setdefault('providers', {})['llamacpp'] = {'base_url': endpoint, 'model': model, 'api_key': 'local-only'}
    config['fallback_providers'] = []
    config.pop('fallback_model', None)
    for name in ('compression', 'title_generation', 'approval', 'skills_hub', 'mcp', 'curator'):
        config.setdefault('auxiliary', {}).setdefault(name, {}).update(
            provider='main', model='', base_url='', api_key='', fallback_chain=[])
    config.setdefault('delegation', {}).update(backend='default', model=model, base_url=endpoint,
        api_key='local-only', fallback_providers=[], max_concurrent_children=1, subagent_auto_approve=False)
    config.setdefault('auth', {})['adopt_external_logins'] = False
    config.setdefault('telemetry', {}).setdefault('shared_metrics', {}).update(enabled=False, send=False)
    config.setdefault('stt', {}).update(enabled=True, provider='local', language='en')
    config['stt'].setdefault('local', {}).update(model='base', device='cpu', compute_type='int8', vad=True)
    config.setdefault('tts', {}).update(provider='piper')
    config['tts'].setdefault('piper', {}).update(voice='en_US-lessac-medium', use_cuda=False)
    return config


def install(home, endpoint, model, dry_run=False):
    from ruamel.yaml import YAML
    home = Path(home).expanduser().resolve()
    yaml = YAML()
    yaml.preserve_quotes = True
    config_path, soul_path = home / 'config.yaml', home / 'SOUL.md'
    config = yaml.load(config_path.read_text(encoding='utf-8')) if config_path.exists() else {}
    config = local_settings(config or {}, endpoint, model)
    output = io.StringIO()
    yaml.dump(config, output)
    skill = (ROOT / 'jarvis' / 'skills' / 'jarvis-workspace' / 'SKILL.md').read_text(encoding='utf-8')
    soul = soul_path.read_text(encoding='utf-8') if soul_path.exists() else ''
    if MARKER not in soul:
        soul += (f'\n\n{MARKER}\n\n'
            'Use the jarvis-workspace skill for the local knowledge vault and content workflows. '
            f'The vault is at `{home / "jarvis-data" / "vault"}`. '
            'Local inference and local speech are configured; do not promise that terminal tools '
            'or web tasks are offline. Keep important source verification explicit.\n')
    launcher = ('@echo off\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "' +
                str(ROOT / 'scripts' / 'Start-Jarvis.ps1') + '" -HermesHome "' + str(home) + '"\n')
    files = {
        'config.yaml': output.getvalue(), 'SOUL.md': soul,
        'skills/productivity/jarvis-workspace/SKILL.md': skill,
        'Jarvis-Local.cmd': launcher,
        'jarvis-data/settings.json': json.dumps({'endpoint': endpoint, 'model': model}, indent=2),
    }
    if dry_run:
        print(json.dumps({'dry_run': True, 'files': list(files), 'vault': 'jarvis-data/vault',
            'changes': 'Local inference routes, no model fallbacks, local speech, telemetry off, external login adoption off; unrelated settings preserved.'}, indent=2))
        return None
    backup = home / 'backups' / ('jarvis-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    backup.mkdir(parents=True)
    manifest = {'home': str(home), 'files': {}}
    for name, text in files.items():
        destination = home / name
        manifest['files'][name] = {'before': destination.read_text(encoding='utf-8') if destination.exists() else None,
                                 'installed': text}
    atomic_write(backup / 'manifest.json', json.dumps(manifest, indent=2))
    try:
        for name, text in files.items():
            atomic_write(home / name, text)
        vault = Vault(home / 'jarvis-data' / 'vault')
        map_path = vault.root / 'VAULT.md'
        if not map_path.exists():
            atomic_write(map_path, '# Jarvis vault\n\nraw/: captured material.\nwiki/: organized reference notes.\noutputs/: model drafts.\n\nFolder placement is not evidence of religious or factual approval. Supply source notes explicitly. Open this folder in Obsidian using Open folder as vault.\n')
    except Exception:
        restore(backup)
        raise
    print(json.dumps({'installed': True, 'backup': str(backup), 'launcher': str(home / 'Jarvis-Local.cmd')}, indent=2))
    return backup


def restore(backup):
    backup = Path(backup).resolve()
    manifest = json.loads((backup / 'manifest.json').read_text(encoding='utf-8'))
    home = Path(manifest['home']).resolve()
    if backup.parent != home / 'backups' or not backup.name.startswith('jarvis-'):
        raise ValueError('Backup must be in this Hermes home’s backups/jarvis-* directory.')
    # Validate every destination and detect later edits before changing any file.
    changes = []
    for name, entry in manifest['files'].items():
        destination = (home / name).resolve()
        if not destination.is_relative_to(home):
            raise ValueError('Invalid backup destination.')
        if not destination.exists() and entry['before'] is None:
            continue
        current = destination.read_text(encoding='utf-8') if destination.exists() else None
        if current != entry['installed']:
            raise ValueError(f'{name} changed after installation; inspect it before manually restoring the backup.')
        changes.append((destination, entry['before']))
    for destination, before in changes:
        if before is None:
            destination.unlink(missing_ok=True)
        else:
            atomic_write(destination, before)
    print('Restored installation files. User vault notes and outputs were preserved.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hermes-home')
    parser.add_argument('--endpoint', default='http://127.0.0.1:8080/v1')
    parser.add_argument('--model', default='local-hermes')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--restore')
    args = parser.parse_args()
    if args.restore:
        restore(args.restore)
    elif args.hermes_home:
        install(args.hermes_home, args.endpoint, args.model, args.dry_run)
    else:
        parser.error('--hermes-home or --restore is required')


if __name__ == '__main__':
    main()
