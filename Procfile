# --workers 1 is load-bearing: the §5 run.json stash in app.py lives in one process's memory
# (mirrors the sibling sentiment repo's in-memory job store). Keep in sync with gunicorn.conf.py.
web: gunicorn app:app --bind 0.0.0.0:$PORT --timeout 300 --workers 1
