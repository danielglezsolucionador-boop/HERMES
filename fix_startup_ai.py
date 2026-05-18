with open('app/main.py', 'r', encoding='utf-8') as f:
    src = f.read()

old = 'from app.runner.task_runner import runner_loop, recovery_scan'
new = 'from app.runner.task_runner import runner_loop, recovery_scan\nfrom app.integrations.claude_client import validate_startup'

old2 = '    await recovery_scan()'
new2 = '    validate_startup()\n    await recovery_scan()'

if 'validate_startup' not in src:
    src = src.replace(old, new, 1)
    src = src.replace(old2, new2, 1)
    with open('app/main.py', 'w', encoding='utf-8') as f:
        f.write(src)
    print('OK main.py — validate_startup agregado')
else:
    print('SKIP main.py — validate_startup ya existe')