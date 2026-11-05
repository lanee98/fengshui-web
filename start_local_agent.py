"""Local launcher: accept credentials through hidden terminal input only."""
import getpass
import os
import runpy
from pathlib import Path

os.environ.setdefault('ZHIPU_MODEL', 'glm-4-flash-250414')

if not os.environ.get('ZHIPU_API_KEY'):
    os.environ['ZHIPU_API_KEY'] = getpass.getpass('Zhipu API key (hidden; Enter to skip): ').strip()
runpy.run_path(str(Path(__file__).with_name('run_preview.py')), run_name='__main__')
