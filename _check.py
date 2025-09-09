import sys
print('PY:', sys.version)
print('EXE:', sys.executable)
import autogen, openai, dotenv, git
print('autogen ok; version:', getattr(autogen, '__version__', 'unknown'))
