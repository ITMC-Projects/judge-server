"""Production env validation without displaying credentials or executing env contents."""
import os
from pathlib import Path
import re
import stat
import subprocess
import sys


def read(path):
    if not path.is_file():
        raise ValueError('Run make prod-init first: missing ' + path.name)
    result = {}
    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        key, sep, value = line.partition('=')
        if not sep or not re.fullmatch(r'[A-Z][A-Z0-9_]*', key) or key in result:
            raise ValueError('Invalid/duplicate environment key')
        result[key] = value
    return result


def initialize(root):
    path = root / 'judge.env'
    values = read(path)
    updates = {}
    if not values.get('DMOJ_JUDGE_KEY'):
        updates['DMOJ_JUDGE_KEY'] = os.environ['JUDGE_INIT_SECRET']
    if not values.get('OJ_PROBLEMS_DIR'):
        updates['OJ_PROBLEMS_DIR'] = (root.parent.parent / 'ITMC-OJ-docker/dmoj/production/data/problems').resolve().as_posix()
    text = path.read_text()
    for key, value in updates.items():
        if key in values:
            text = re.sub(r'^' + key + r'=.*$', lambda _: key + '=' + value, text, flags=re.M)
        else:
            text = text.rstrip() + '\n' + key + '=' + value + '\n'
    if updates:
        path.write_text(text)
    prepare_permissions(root, require_problems=False)


def prepare_permissions(root, require_problems=True):
    """Repair only the exact bind roots/config; never recurse or change env content."""
    values = read(root / 'judge.env')
    problems = Path(values['OJ_PROBLEMS_DIR'])
    targets = [(root / 'judge.env', 0o600), (root / 'config/judge.yml', 0o644)]
    if problems.is_dir():
        targets.append((problems, 0o755))
    elif require_problems:
        raise ValueError('OJ_PROBLEMS_DIR is missing; start OJ production first')
    for path, mode in targets:
        try:
            if stat.S_IMODE(path.stat().st_mode) != mode:
                path.chmod(mode)
        except OSError as error:
            raise ValueError('Cannot set %o permissions on %s; run chmod %o on this exact path '
                             'as its owner, then retry make prod.' % (mode, path, mode)) from error


def validate(root, network=False):
    values = read(root / 'judge.env')
    keys = ('DMOJ_JUDGE_NAME', 'DMOJ_JUDGE_KEY', 'OJ_NETWORK', 'OJ_BRIDGE_HOST', 'OJ_BRIDGE_PORT', 'OJ_PROBLEMS_DIR')
    for key in keys:
        value = values.get(key, '')
        if not value or value != value.strip() or any(w in value.lower() for w in ('replace-', 'changeme', '<', 'example.')):
            raise ValueError('Missing/placeholder setting: ' + key)
        if any(c in value for c in "'\"$`\r\n#"):
            raise ValueError('Use literal unquoted values without interpolation: ' + key)
    key = values['DMOJ_JUDGE_KEY']
    if len(key) < 32 or len(set(key)) < 8:
        raise ValueError('Judge key requires at least 32 strong random characters')
    for name in ('DMOJ_JUDGE_NAME', 'OJ_NETWORK', 'OJ_BRIDGE_HOST'):
        if not re.fullmatch(r'[a-zA-Z0-9_.-]+', values[name]):
            raise ValueError('Invalid name/hostname: ' + name)
    if not values['OJ_BRIDGE_PORT'].isdigit() or not 1 <= int(values['OJ_BRIDGE_PORT']) <= 65535:
        raise ValueError('Invalid OJ_BRIDGE_PORT')
    directory = Path(values['OJ_PROBLEMS_DIR'])
    if not directory.is_absolute() or not directory.is_dir():
        raise ValueError('OJ_PROBLEMS_DIR must be an existing absolute directory; start OJ production first')
    if not (root / 'config/judge.yml').is_file():
        raise ValueError('Missing production/config/judge.yml; run make prod-init')
    if network:
        result = subprocess.run(['docker', 'network', 'inspect', values['OJ_NETWORK']], capture_output=True)
        if result.returncode:
            raise ValueError('OJ Docker network unavailable; start OJ with make prod on the same VPS first')
    print('Judge production configuration validated (key hidden).')


if __name__ == '__main__':
    try:
        action = sys.argv[1]
        if action == '--init':
            initialize(Path(sys.argv[2]))
        elif action == '--permissions':
            prepare_permissions(Path(sys.argv[2]))
            print('Judge bind permissions ready: problems=755, config=644, env=600.')
        else:
            validate(Path(sys.argv[2] if action == '--network' else action), action == '--network')
    except (ValueError, OSError) as error:
        sys.exit('ERROR: ' + str(error))
