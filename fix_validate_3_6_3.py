import asyncio
from app.ai.context_builder import build_context

async def main():
    ctx = await build_context()
    print('OK context generado')
    print('  tasks incluidas  :', len(ctx.get('tasks', [])))
    print('  incidents        :', len(ctx.get('incidents', [])))
    print('  summary          :', ctx.get('summary', ''))
    isolation = ctx.get('_isolation', {})
    print('  total_chars      :', isolation.get('total_chars', 0))
    print('  truncated        :', isolation.get('truncated', False))
    meta = ctx.get('metadata', {})
    print('  runtime_status   :', meta.get('runtime', ''))
    print('  generated_at     :', meta.get('generated_at', ''))
    print('  context_version  :', meta.get('context_version', ''))
    print('VALIDACION OK')

asyncio.run(main())