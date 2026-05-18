with open('app/runner/task_runner.py', 'r', encoding='utf-8') as f:
    src = f.read()

old = '                logger.debug("runner: sin tasks pending, durmiendo %ds", POLL_INTERVAL)\n                await asyncio.sleep(POLL_INTERVAL)\n                continue'
new = '                logger.debug("runner: sin tasks pending, durmiendo %ds", POLL_INTERVAL)\n                runtime_status.mark_loop()\n                await asyncio.sleep(POLL_INTERVAL)\n                continue'

if old in src:
    src = src.replace(old, new, 1)
    with open('app/runner/task_runner.py', 'w', encoding='utf-8') as f:
        f.write(src)
    print('OK mark_loop en continue agregado')
else:
    print('ERROR — patron no encontrado')