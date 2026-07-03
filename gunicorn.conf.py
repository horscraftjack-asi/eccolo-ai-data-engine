import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8080')}"
# Single worker is load-bearing: the §5 run.json stash in app.py is in-process memory (mirrors
# the sibling sentiment repo's in-memory job store). Do not raise without moving to an external
# store (Redis). Keep in sync with the Procfile.
workers = 1
timeout = 300       # Claude API calls can take 60-120s on long prompts
