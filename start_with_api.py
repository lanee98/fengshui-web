"""Prompt without echo; retain the provider key only in this process environment."""
import getpass
import os
import runpy
from pathlib import Path

if __name__ == '__main__':
    if not os.environ.get('AHOLO_API_KEY'):
        os.environ['AHOLO_API_KEY'] = getpass.getpass('AHOLO API key (not saved): ')
    runpy.run_path(str(Path(__file__).parent/'run_preview.py'),run_name='__main__')
