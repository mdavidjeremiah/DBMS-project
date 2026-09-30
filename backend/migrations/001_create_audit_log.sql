-- MySQL migration for installations that use manual schema migrations.
-- The application also creates this table automatically through SQLAlchemy on startup.
CREATE TABLE IF NOT EXISTS audit_log (
    auditlogid INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    username_or_email VARCHAR(100) NULL,
    action VARCHAR(64) NOT NULL,
    details TEXT NULL,
    ip_address VARCHAR(45) NULL,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_audit_log_user FOREIGN KEY (user_id)
        REFERENCES employee(employeeid) ON DELETE SET NULL,
    INDEX ix_audit_log_user_id (user_id),
    INDEX ix_audit_log_username_or_email (username_or_email),
    INDEX ix_audit_log_action (action),
    INDEX ix_audit_log_timestamp (timestamp)
);
