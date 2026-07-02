"""
Ziggurat Analytics Engine — web UI
Upload Meta CSV exports, pick a client, download the scored performance workbook.
Reuses core/build_workbook.py unchanged — same logic as the skill, one source of truth.

Produces fully-built data tabs plus Claude-written insight sections in a single /run:
run_build() calls core/insights.py inline. If ANTHROPIC_API_KEY is unset (or the call
fails), it degrades gracefully to labelled insight shells with a note — no separate step.
"""
import os
import glob
import json
import tempfile
from urllib.parse import quote
from flask import Flask, request, render_template, send_file, jsonify
from flask_cors import CORS

from core import build_workbook as bw

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB upload cap

# Lock CORS to the frontend's origin in production. Set FRONTEND_ORIGIN to the
# unified frontend's URL (comma-separated for multiple). Unset -> "*", so this
# app's own Jinja page (same-origin, unaffected by CORS either way) and local
# dev keep working. Mirrors the pattern in eccolo-ai-scraper-sentiment/app.py so
# both backends configure the same way.
_origins_env = os.environ.get("FRONTEND_ORIGIN", "").strip()
_origins = [o.strip() for o in _origins_env.split(",") if o.strip()] or "*"
CORS(app, resources={r"/api/*": {"origins": _origins}, r"/run": {"origins": _origins}})

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "configs")


def available_clients():
    """List bundled clients by their config files, so the dropdown self-populates."""
    clients = []
    for path in sorted(glob.glob(os.path.join(CONFIG_DIR, "*-analytics-config.md"))):
        cfg = bw.parse_config(path)
        clients.append({"slug": cfg.client_slug, "name": cfg.client_name, "path": path,
                        "platforms_active": cfg.platforms_active})
    return clients


@app.route("/api/clients", methods=["GET"])
def api_clients():
    """JSON client list for an external frontend's dropdown — same source as the
    Jinja page's own list, just without the HTML. Mirrors the sentiment-analyzer's
    /sentiment/options pattern so both tools' frontends self-populate the same way."""
    return jsonify({
        "clients": [
            {"slug": c["slug"], "name": c["name"], "platforms_active": c["platforms_active"]}
            for c in available_clients()
        ],
    })


@app.route("/")
def index():
    clients = available_clients()
    # Build a slug -> platforms_active map for the frontend badge logic
    client_platforms = {c["slug"]: c["platforms_active"] for c in clients}
    # If set, the Result screen's "Scrape top video" flywheel hop links to the deployed
    # Comment Scraper frontend with the top YouTube post's URL pre-filled. Unset -> hidden.
    scraper_url = os.environ.get("SCRAPER_URL", "").strip().rstrip("/")
    return render_template("index.html", clients=clients, client_platforms=client_platforms,
                           scraper_url=scraper_url)


@app.route("/run", methods=["POST"])
def run():
    client_slug = request.form.get("client")
    clients = {c["slug"]: c for c in available_clients()}

    # Config resolution mirrors the skill: uploaded config wins, else bundled by slug.
    uploaded_config = request.files.get("config")
    workdir = tempfile.mkdtemp()
    if uploaded_config and uploaded_config.filename:
        config_path = os.path.join(workdir, "uploaded-config.md")
        uploaded_config.save(config_path)
    elif client_slug in clients:
        config_path = clients[client_slug]["path"]
    else:
        return jsonify({"error": "No config: pick a client or upload a config file."}), 400

    # Save whichever CSVs were provided (Meta + YouTube)
    paths = {}
    for field, plat in (
        ("fb",          "facebook"),
        ("ig",          "instagram"),
        ("stories",     "stories"),
        ("yt",          "youtube"),          # combined YT Table data — auto-split by Duration
        ("yt_shorts",   "youtube_shorts"),   # pre-split Shorts export
        ("yt_longform", "youtube_longform"), # pre-split long-form export
    ):
        f = request.files.get(field)
        if f and f.filename:
            p = os.path.join(workdir, f"{field}.csv")
            f.save(p)
            paths[plat] = p
    if not paths:
        return jsonify({"error": "Upload at least one CSV (Facebook, Instagram, Stories, or YouTube)."}), 400

    # Drive the same core the skill uses. run_build() is a thin wrapper we add to the core
    # so both the CLI and the web app call one function rather than re-implementing main().
    try:
        result = bw.run_build(config_path=config_path, csv_paths=paths,
                              month=request.form.get("month") or None, out_dir=workdir)
    except bw.MissingColumns as e:
        return jsonify({"error": "Column mismatch — Meta may have renamed a header.",
                        "detail": e.detail}), 422
    except Exception as e:
        return jsonify({"error": f"Build failed: {e}"}), 500

    resp = send_file(result["output"], as_attachment=True,
                     download_name=os.path.basename(result["output"]))
    # Expose build notes + stats to the frontend's result screen. Header values must be
    # Latin-1 safe, so anything that isn't plain ASCII (client names, notes) is URL-quoted.
    insight_note = next((n for n in result.get("notes", [])
                         if "insight" in n.lower() or "claude" in n.lower()), "")
    other_notes = [n for n in result.get("notes", []) if n != insight_note]
    resp.headers["X-Insight-Note"] = quote(insight_note)
    resp.headers["X-Client"] = quote(result.get("client") or "")
    resp.headers["X-Month"] = quote(result.get("month") or "")
    resp.headers["X-Counts"] = quote(json.dumps(result.get("counts") or {}))
    resp.headers["X-Notes"] = quote(json.dumps(other_notes))
    resp.headers["X-Top-Posts"] = quote(json.dumps(result.get("top_posts") or []))
    # Contract §1.3 provenance block — same URL-quoted convention as the other metadata headers.
    resp.headers["X-Provenance"] = quote(json.dumps(result.get("provenance") or {}))
    resp.headers["Access-Control-Expose-Headers"] = (
        "X-Insight-Note, X-Client, X-Month, X-Counts, X-Notes, X-Top-Posts, X-Provenance"
    )
    return resp


if __name__ == "__main__":
    # Railway provides PORT; default 8080 for local runs.
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
