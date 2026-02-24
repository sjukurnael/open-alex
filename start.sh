#!/bin/sh
# Run full load only if the database is empty, then start the API.
python -c "
from database import init_db, is_empty
init_db()
if is_empty():
    print('Database is empty — starting full load in background.')
    import subprocess, sys
    subprocess.Popen([sys.executable, 'load.py'])
else:
    print('Database already populated — skipping full load.')
"
uvicorn api:app --host 0.0.0.0 --port 8080
