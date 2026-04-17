# Database Migrations

This directory contains SQL migration files for the database schema.

## Naming Convention
- Format: `XXX_name.sql` where XXX is a 3-digit sequential number
- Example: `001_users.sql`, `002_withdrawals.sql`

## Migration Order
Migrations are applied in numerical order. Always add new migrations with the next available number.

## Creating a New Migration
1. Create a new file with the next number
2. Write SQL statements (CREATE, ALTER, etc.)
3. Include both UP and DOWN migrations (commented)

Example:
```sql
-- UP
CREATE TABLE example (...);

-- DOWN
DROP TABLE example;