"""Canonical account codes used by workflow postings."""
import models
ACCOUNTS = {
 "1010":("Cash","ASSET"),"1020":("Bank","ASSET"),"1030":("Mobile money","ASSET"),
 "1040":("Accounts receivable","ASSET"),"1050":("Inventory","ASSET"),
 "2010":("Accounts payable","LIABILITY"),"2020":("Payroll payable","LIABILITY"),
 "2030":("Payroll deductions payable","LIABILITY"),"3010":("Opening equity","EQUITY"),
 "4010":("Sales revenue","REVENUE"),"5010":("Cost of goods sold","EXPENSE"),
 "5020":("Salaries and wages","EXPENSE"),"5030":("Inventory shrinkage","EXPENSE")}
def ensure_accounts(db):
    existing={a.account_code for a in db.query(models.ChartOfAccount)}
    for code,(name,kind) in ACCOUNTS.items():
        if code not in existing: db.add(models.ChartOfAccount(account_code=code,account_name=name,account_type=kind,balance=0))
    db.flush()
