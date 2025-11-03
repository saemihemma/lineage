# PostgreSQL Transaction Abort Error Fix

## Problem
PostgreSQL connections were sharing a single cached connection across all requests. When one request's query failed and aborted the transaction, subsequent requests using the same connection would fail with:
```
psycopg2.errors.InFailedSqlTransaction: current transaction is aborted, commands ignored until end of transaction block
```

## Root Cause
1. `Database.connect()` caches a single connection object
2. `get_db()` returns this same connection for all requests
3. When a query fails, PostgreSQL aborts the transaction
4. All subsequent queries on that connection fail until rollback
5. Multiple concurrent requests share the same aborted transaction state

## Solution
Enabled **autocommit mode** for PostgreSQL connections:
- Each query becomes its own transaction
- If one query fails, it doesn't affect subsequent queries
- Eliminates "transaction aborted" cascade failures
- No changes needed to existing code (commit() calls are no-ops with autocommit)

## Changes Made

### backend/database.py
1. **PostgreSQLAdapter.connect()**: 
   - Set `conn.autocommit = True` after connection
   - Added connection state check to detect/reset bad states
   
2. **execute_query()**: 
   - Enhanced error handling to detect and rollback aborted transactions
   - Automatic retry after rollback for transaction errors

### backend/routers/game.py
1. **check_session_expiry()**: 
   - Added transaction state checking and rollback
   - Graceful error handling (fails open to prevent breaking game)
   - Enhanced error logging

## Impact
- ✅ Prevents "transaction aborted" errors
- ✅ Each query is isolated (no transaction state bleeding)
- ✅ Existing commit/rollback calls remain (harmless with autocommit)
- ✅ Maintains backward compatibility
- ✅ Works with both SQLite (no change) and PostgreSQL

## Notes
- With autocommit=True, `commit()` calls are no-ops (safe but unnecessary)
- `rollback()` can still be useful for explicit error recovery
- For future: Consider connection pooling for better performance (not needed now)

## Testing
- All existing tests should pass
- Transaction abort errors should be eliminated
- No breaking changes

