"""Seed missing workflow posting accounts without changing existing accounts."""
from alembic import op
import sqlalchemy as sa
revision="0012_workflow_accounts"
down_revision="0011_data_quality"
branch_labels=depends_on=None
ACCOUNTS=[('1010','Cash','ASSET'),('1020','Bank','ASSET'),('1030','Mobile money','ASSET'),('1040','Accounts receivable','ASSET'),('1050','Inventory','ASSET'),('2010','Accounts payable','LIABILITY'),('2020','Payroll payable','LIABILITY'),('2030','Payroll deductions payable','LIABILITY'),('3010','Opening equity','EQUITY'),('4010','Sales revenue','REVENUE'),('5010','Cost of goods sold','EXPENSE'),('5020','Salaries and wages','EXPENSE'),('5030','Inventory shrinkage','EXPENSE')]
def upgrade():
    c=op.get_bind()
    for code,name,kind in ACCOUNTS:
        if not c.execute(sa.text('SELECT account_code FROM chart_of_accounts WHERE account_code=:code'),{'code':code}).first():
            c.execute(sa.text('INSERT INTO chart_of_accounts(account_code,account_name,account_type,balance) VALUES(:code,:name,:kind,0)'),{'code':code,'name':name,'kind':kind})
def downgrade():
    pass # Posting accounts may be referenced by real journals; retain them.
