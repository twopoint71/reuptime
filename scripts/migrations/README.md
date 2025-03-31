# Database Migrations

This directory contains database migration scripts for the Reuptime application.

## Structure

- `__init__.py`: Migration runner that manages the execution of migrations
- `001_add_uuid_to_hosts.py`: Adds UUID columns to hosts tables
- `README.md`: This file

## Running Migrations

To run migrations, you can use the migration runner:

```python
from scripts.migrations import run_migrations
from db import get_default_db_path

config = {'DATABASE': get_default_db_path()}
run_migrations(config)
```

## Adding New Migrations

1. Create a new Python file in this directory with a numeric prefix (e.g., `002_...`)
2. Implement a `migrate(config)` function that performs the migration
3. The migration runner will automatically detect and run new migrations

## Migration History

The migration runner maintains a `migrations` table in the database to track which migrations have been applied. This ensures that migrations are only run once and in the correct order.

## Rollback

If a migration fails, it will automatically rollback any changes made during that migration. However, successfully applied migrations cannot be automatically rolled back. If you need to undo a migration, you'll need to create a new migration that reverses the changes.