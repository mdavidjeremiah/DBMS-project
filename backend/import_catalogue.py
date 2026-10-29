"""Import the reviewed catalogue without replacing existing products or stock."""
import argparse
import csv
from decimal import Decimal
from pathlib import Path
from sqlalchemy import func
import models

CATALOGUE = Path(__file__).parent / 'data' / 'hardware_products.csv'

def import_catalogue(db, source=CATALOGUE):
    rows=list(csv.DictReader(source.open(encoding='utf-8')))
    if len(rows)!=200 or len({r['itemname'].strip().casefold() for r in rows})!=200:
        raise ValueError('Expected 200 distinct catalogue items')
    existing={n.strip().casefold() for (n,) in db.query(models.Product.itemname)}
    categories={c.categoryname.strip().casefold():c for c in db.query(models.Category)}
    added=0
    for row in rows:
        if row['itemname'].strip().casefold() in existing:
            continue
        key=row['category'].strip().casefold()
        if key not in categories:
            categories[key]=models.Category(categoryname=row['category'])
            db.add(categories[key]);db.flush()
        db.add(models.Product(itemname=row['itemname'],categoryid=categories[key].categoryid,
            base_unit=row['base_unit'],description=row['description'],unitprice=Decimal(row['unitprice']),
            costprice=Decimal(row['costprice']),reorderlevel=int(row['reorderlevel']),is_active=False))
        existing.add(row['itemname'].strip().casefold());added+=1
    db.flush()
    return {'added':added,'skipped':len(rows)-added,'awaiting_pricing':added}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true',help='Commit catalogue additions; otherwise preview and roll back')
    args=parser.parse_args()
    from database import SessionLocal
    from sqlalchemy import inspect
    with SessionLocal() as db:
        if not {'product','category'} <= set(inspect(db.get_bind()).get_table_names()):
            raise SystemExit('Run alembic upgrade head before importing')
        try:
            result=import_catalogue(db)
            if args.apply: db.commit()
            else: db.rollback()
            print(('IMPORTED' if args.apply else 'PREVIEW ONLY'),result)
        except Exception:
            db.rollback()
            raise
