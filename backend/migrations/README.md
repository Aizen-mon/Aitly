This folder contains the local Alembic migration scaffold for the AI Tally backend.

The current app still creates tables on startup for local development, but the migration
files here make it straightforward to switch to explicit revision-based upgrades.

Suggested commands:

```powershell
cd backend
alembic upgrade head
```
