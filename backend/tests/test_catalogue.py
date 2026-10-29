from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from decimal import Decimal
import models
from import_catalogue import import_catalogue
from api_workflow_routes import product_pricing
import schemas
from unittest.mock import patch

def test_catalogue_has_200_products_and_can_be_repeated_without_overwriting():
    engine=create_engine("sqlite://")
    models.Base.metadata.create_all(engine)
    with Session(engine) as db:
        assert import_catalogue(db)=={"added":200,"skipped":0,"awaiting_pricing":200}
        db.commit()
        assert db.query(models.Product).count()==200
        assert db.query(models.Category).count()==20
        assert db.query(models.InventoryBalance).count()==0
        assert not any(p.is_active for p in db.query(models.Product))
        product=db.query(models.Product).first(); product.unitprice=Decimal('5000');db.commit()
        assert import_catalogue(db)['added']==0
        assert product.unitprice==Decimal('5000')

def test_catalogue_import_rolls_back_atomically():
    engine=create_engine("sqlite://")
    models.Base.metadata.create_all(engine)
    with Session(engine) as db:
        import_catalogue(db);db.rollback()
        assert db.query(models.Product).count()==0


def test_product_pricing_makes_imported_product_usable_without_inventing_stock():
    engine=create_engine("sqlite://")
    models.Base.metadata.create_all(engine)
    with Session(engine) as db:
        import_catalogue(db)
        user=models.Employee(name="Inventory manager",nin="CATALOGUE-MGR",roletype=models.RoleType.BRANCH_MANAGER)
        db.add(user);db.commit()
        product=db.query(models.Product).first()
        result=product_pricing(product.itemid,schemas.ProductPricingUpdate(unitprice='25000',costprice='20000'),user,db)
        assert result['is_active']
        assert result['unitprice']=='25000.00'
        assert db.query(models.InventoryBalance).count()==0
