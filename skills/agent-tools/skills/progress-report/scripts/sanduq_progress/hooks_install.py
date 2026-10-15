"""`progress hooks install|uninstall|status`: native host hooks that call scripts/hook.py.

Claude Code reads `.claude/settings.json` (project) or `~/.claude/settings.json` (user); Codex reads `.codex/hooks.json`
(project) or `~/.codex/hooks.json` (user). Both use the same shape:

    {"hooks": {"<Event>": [{"matcher": "<regex, optional>", "hooks": [{"type": "command", "command": "...", "timeout": 10}]}]}}

Every entry written here carries the argument `--managed-by=progress-report` in its command. That tag is how uninstall
finds exactly its own entries and nothing else; the rest of the file is preserved (key order, other hooks, other
settings). Spec Kit registers Progress through its own event dispatcher (`speckit.progress.hook-*`); when such hooks are
present this installer refuses, so one event is never recorded twice.
"""
import json
import os
import sys
from pathlib import Path

from .paths import inside
from .util import ProgressError, atomic_write

TAG = '--managed-by=progress-report'
SPECKIT_MARK = 'speckit.progress.hook'
TIMEOUT = 10
SUBAGENT_MATCHER = 'Task|Agent|spawn_agent'
HOOK_SCRIPT = Path(__file__).resolve().parent.parent / 'hook.py'

# (host event name, hook.py event, matcher). Codex documents no session end event: its Stop already forces a final refresh.
CLAUDE_EVENTS = (('SessionStart', 'session_start', None), ('PreToolUse', 'pre_tool_use', SUBAGENT_MATCHER),
                 ('PostToolUse', 'post_tool_use', None), ('Stop', 'stop', None), ('SessionEnd', 'session_end', None))
CODEX_EVENTS = tuple(e for e in CLAUDE_EVENTS if e[0] != 'SessionEnd')
EVENTS = {'claude': CLAUDE_EVENTS, 'codex': CODEX_EVENTS}


def refused(code, message):
    return ProgressError(code, message, 3)


def home():
    return Path(os.environ.get('SANDUQ_PROGRESS_HOME') or Path.home())


def settings_path(root, host, scope):
    if scope == 'project':
        return Path(root) / ('.claude/settings.json' if host == 'claude' else '.codex/hooks.json')
    if host == 'claude':
        base = Path(os.environ['CLAUDE_CONFIG_DIR']) if os.environ.get('CLAUDE_CONFIG_DIR') else home() / '.claude'
        return base / 'settings.json'
    base = Path(os.environ['CODEX_HOME']) if os.environ.get('CODEX_HOME') else home() / '.codex'
    return base / 'hooks.json'


def shown(root, path):
    path = Path(path)
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        pass
    try:
        return '~/' + path.relative_to(home()).as_posix()
    except ValueError:
        return path.name


def load(path):
    """The settings document, {} when the file does not exist. A file that is not a JSON object is never overwritten."""
    try:
        text = Path(path).read_text(encoding='utf-8')
    except FileNotFoundError:
        return {}
    except OSError as exc:
        raise refused('PROGRESS_HOOKS_SETTINGS', f'cannot read {Path(path).name}: {type(exc).__name__}') from None
    if not text.strip():
        return {}
    try:
        data = json.loads(text)
    except ValueError:
        raise refused('PROGRESS_HOOKS_SETTINGS', f'{Path(path).name} is not valid JSON; fix it first') from None
    if not isinstance(data, dict) or not isinstance(data.get('hooks', {}), dict):
        raise refused('PROGRESS_HOOKS_SETTINGS', f'{Path(path).name} has an unexpected "hooks" shape; not touching it')
    return data


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def has_speckit(data):
    return any(SPECKIT_MARK in text for text in strings(data.get('hooks', {})))


def is_ours(handler):
    command = handler.get('command') if isinstance(handler, dict) else None
    return isinstance(command, str) and TAG in command and 'hook.py' in command


def own_count(data):
    count = 0
    for groups in data.get('hooks', {}).values():
        for group in groups if isinstance(groups, list) else []:
            count += sum(1 for h in group.get('hooks', []) if is_ours(h)) if isinstance(group, dict) and isinstance(group.get('hooks'), list) else 0
    return count


def python_command(override):
    return override or ('python' if sys.platform == 'win32' else 'python3')


def command_for(root, host, scope, event, python):
    script = HOOK_SCRIPT.resolve()
    if scope == 'project':
        if not inside(script, root):
            raise ProgressError('PROGRESS_HOOKS_PATH', 'the skill is outside this repository; use --scope user or copy the skill into the repo', 3)
        relative = script.relative_to(Path(root).resolve()).as_posix()
        path = f'$CLAUDE_PROJECT_DIR/{relative}' if host == 'claude' else relative
    else:
        path = script.as_posix()
    return f'{python} "{path}" {event} {TAG}'


def strip_own(data):
    """Remove this installer's entries, and the groups and keys that only held them. Returns how many entries went."""
    removed = 0
    hooks = data.get('hooks', {})
    for name in list(hooks):
        groups = hooks[name]
        if not isinstance(groups, list):
            continue
        kept = []
        for group in groups:
            inner = group.get('hooks') if isinstance(group, dict) else None
            if not isinstance(inner, list):
                kept.append(group)
                continue
            left = [h for h in inner if not is_ours(h)]
            removed += len(inner) - len(left)
            if left:
                kept.append({**group, 'hooks': left} if len(left) != len(inner) else group)
        if kept:
            hooks[name] = kept
        else:
            del hooks[name]
    if 'hooks' in data and not hooks:
        del data['hooks']
    return removed


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(path, json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def install(root, host, scope, python):
    path = settings_path(root, host, scope)
    for other in ('project', 'user'):
        found = settings_path(root, host, other)
        if has_speckit(load(found)):
            raise refused('PROGRESS_HOOKS_SPECKIT', f'Spec Kit already registers Progress hooks in {shown(root, found)}; remove them or keep using the extension')
    data = load(path)
    strip_own(data)
    commands = [command_for(root, host, scope, event, python) for _, event, _ in EVENTS[host]]
    hooks = data.setdefault('hooks', {})
    for (name, _, matcher), command in zip(EVENTS[host], commands):
        group = {'matcher': matcher} if matcher else {}
        group['hooks'] = [{'type': 'command', 'command': command, 'timeout': TIMEOUT}]
        hooks.setdefault(name, [])
        if not isinstance(hooks[name], list):
            raise refused('PROGRESS_HOOKS_SETTINGS', f'{path.name} hooks.{name} is not a list; not touching it')
        hooks[name].append(group)
    write(path, data)
    note = ' (Codex hooks are experimental: enable the codex_hooks feature)' if host == 'codex' else ''
    return f'progress: hooks installed {host} {scope} {len(EVENTS[host])} entries in {shown(root, path)}{note}'


def uninstall(root, host, scope):
    path = settings_path(root, host, scope)
    if not path.is_file():
        return f'progress: hooks removed {host} {scope} 0 entries'
    data = load(path)
    removed = strip_own(data)
    if removed:
        write(path, data)
    return f'progress: hooks removed {host} {scope} {removed} entries from {shown(root, path)}'


def status(root, hosts):
    parts, speckit = [], False
    for host in hosts:
        cells = []
        for scope in ('project', 'user'):
            data = load(settings_path(root, host, scope))
            speckit = speckit or has_speckit(data)
            cells.append(f'{scope} {own_count(data)}/{len(EVENTS[host])}')
        parts.append(f'{host} ' + ' '.join(cells))
    return 'progress: hooks ' + '; '.join(parts) + f"; spec-kit {'yes' if speckit else 'no'}"


def run(a, root):
    """Entry from progress.py. Never touches a host unless asked: install and uninstall need --host."""
    root = Path(root)
    if a.action == 'status':
        print(status(root, (a.host,) if a.host else ('claude', 'codex')))
        return 0
    if not a.host:
        raise ProgressError('PROGRESS_USAGE', f'hooks {a.action} needs --host claude|codex', 2)
    if a.action == 'install':
        print(install(root, a.host, a.scope, python_command(a.python)))
    else:
        print(uninstall(root, a.host, a.scope))
    return 0
