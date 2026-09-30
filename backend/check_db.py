"""Quick DB connectivity probe — tries several common credential combos."""
import sys
sys.path.insert(0, '.')

import pymysql

combos = [
    ('hw_user',  'hw_password',  'hardware_world'),
    ('root',     '',             'hardware_world'),
    ('root',     'root',         'hardware_world'),
    ('root',     'password',     'hardware_world'),
    ('root',     'mysql',        'hardware_world'),
    ('hw_user',  'hw_password',  None),
    ('root',     '',             None),
]

ok = False
for user, pw, db in combos:
    try:
        kw = dict(host='127.0.0.1', port=3306, user=user, password=pw, connect_timeout=3)
        if db:
            kw['database'] = db
        c = pymysql.connect(**kw)
        ver = c.get_server_info()
        c.close()
        print(f"SUCCESS  user={user!r}  password={pw!r}  db={db!r}  server={ver}")
        ok = True
        break
    except Exception as e:
        print(f"FAIL     user={user!r}  password={pw!r}  db={db!r}  err={e}")

if not ok:
    print("\nMySQL is not reachable with any common credentials.")
    print("Please provide your MySQL root password so the DB can be set up.")
    sys.exit(1)
sys.exit(0)
