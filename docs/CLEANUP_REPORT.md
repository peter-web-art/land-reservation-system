# Cleanup Report

## Current Documentation Position

The repository currently contains active application code, runtime assets, and project documentation in place. Earlier cleanup reports referenced archive locations outside this workspace; those references have been removed from the active documentation set because they are not reliable for the current environment.

## Active Top-Level Folders In This Workspace

- `accounts`
- `docs`
- `lands`
- `land_reservation`
- `media`
- `scripts`
- `static`
- `templates`
- `venv`

## Active Top-Level Project Files

- `.env.example`
- `.gitignore`
- `db.sqlite3`
- `manage.py`
- `README.md`
- `requirements.txt`

## Current Recommendation

- Treat the text files in `docs/` and `README.md` as the active source of project documentation.
- Regenerate or archive older binary documentation files if they are no longer maintained.
- Keep future cleanup notes tied to this workspace only, not to external machine-specific archive paths.
