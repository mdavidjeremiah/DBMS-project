# Data integrity decisions

InventoryBalance is the intended stock source because POS, returns, transfers and the receipt service already use it. Existing ERP stock tables and legacy routes still require reconciliation before removal; their quantities must not be blindly added because they may represent the same stock.

Procurement model class names now match their business concepts while preserving existing physical table and column names. Explicit SQLAlchemy synonyms support callers during consolidation. The service owns receipt, invoice and payment posting.

Database views provide inventory position and trial balance without storing another calculated copy. Stock quality triggers reject negative balances. Stock transaction logs are written by database triggers within the same transaction, while AuditLog records the actor and business event. Recovery logs remain the database server's responsibility.
