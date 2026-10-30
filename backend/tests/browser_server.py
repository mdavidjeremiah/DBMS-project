"""Isolated local browser test server. Never use this test app in production."""
import os,secrets,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['APP_ENV']='test'
os.environ['DATABASE_URL']='sqlite://'
os.environ['SECRET_KEY']=secrets.token_urlsafe(48)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import Depends
import models,main,auth
from database import get_db
from accounting_setup import ensure_accounts
import tempfile
_test_directory=tempfile.TemporaryDirectory(prefix='hw-browser-')
engine=create_engine('sqlite:///'+str(Path(_test_directory.name)/'browser.sqlite'),connect_args={'check_same_thread':False})
models.Base.metadata.create_all(engine)
Factory=sessionmaker(bind=engine)
with Factory() as db:
 b=models.Branch(branchname='Browser Test',location='Test only');db.add(b);db.flush()
 u=models.Employee(name='Workflow Tester',nin='BROWSER-TEST',email='browser@example.com',roletype=models.RoleType.BRANCH_MANAGER,branchid=b.branchid,is_active=True);db.add(u);db.flush()
 role=models.Role(role_name='UI test operator');db.add(role);db.flush()
 for code in sorted(set().union(*[set(codes) for codes in auth.DEFAULT_ROLE_PERMS.values()])):
  module,action=code.split(':',1);p=models.Permission(code=code,module=module,action=action);db.add(p);db.flush();db.add(models.RolePermission(role_id=role.role_id,permission_id=p.permission_id))
 db.add(models.UserRole(user_id=u.employeeid,role_id=role.role_id))
 wh=models.Warehouse(branch_id=b.branchid,warehouse_name='Test warehouse');db.add(wh);db.flush()
 product=models.Product(itemname='Browser test cement',unitprice=200,costprice=100,is_active=True);db.add(product);db.flush()
 db.add(models.InventoryBalance(item_id=product.itemid,warehouse_id=wh.warehouse_id,available_stock=3,reserved_stock=0))
 db.add(models.Product(itemname='Out of stock example',unitprice=100,costprice=50,is_active=True))
 ensure_accounts(db);db.commit()
def test_db():
 with Factory() as db:yield db
def test_user(db=Depends(get_db)):
 return db.query(models.Employee).filter_by(email='browser@example.com').one()
main.app.dependency_overrides[get_db]=test_db
main.app.dependency_overrides[auth.get_current_user]=test_user
if __name__=='__main__':
 import uvicorn
 uvicorn.run(main.app,host='127.0.0.1',port=int(os.getenv('HW_TEST_PORT','8876')),log_level='warning')
