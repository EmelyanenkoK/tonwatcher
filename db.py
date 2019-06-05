import sqlite3

def init_base(db_name = "explorer.db"):
  with sqlite3.connect(db_name) as conn:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    tables = cur.fetchall()
    tables = [i[0] for i in tables]
    if not "blocks" in tables:
      cur.execute("CREATE TABLE blocks(height integer PRIMARY KEY, hash text, timestamp integer)")
    if not "giver_balance" in tables:
      cur.execute("CREATE TABLE giver_balance (id integer PRIMARY KEY AUTOINCREMENT, timestamp integer, balance integer)")

def get_block(height, db_name = "explorer.db"):
  with sqlite3.connect(db_name) as conn:
    cur = conn.cursor()
    cur.execute("SELECT hash from blocks where height=%d"%(int(height)))  
    res = cur.fetchone()
    return res

def get_sequntial_block_hashes(from_height, amount=10):
  with sqlite3.connect(db_name) as conn:
    cur = conn.cursor()
    cur.execute("SELECT height, hash from blocks where height<=%d and height>=%d"%(int(height), int(height)-amount))  
    res = cur.fetchall()
    return res

def insert_block(height, timestamp, long_hash, db_name = "explorer.db"):
  with sqlite3.connect(db_name) as conn:
    cur = conn.cursor()
    cur.execute("INSERT INTO blocks VALUES (?, ?, ?)", (int(height), long_hash, int(timestamp*1000)))

def get_graph_data(db_name = "explorer.db"):
  with sqlite3.connect(db_name) as conn:
    cur = conn.cursor()
    cur.execute("SELECT COUNT(height) from blocks")
    rows=cur.fetchone()[0]
    fr = 1
    if rows>100:
      fr = int(rows/40)
    cur.execute("SELECT height, timestamp from blocks where height%%%d=0 order by height"%(fr))
    rows=cur.fetchall()
    bh = ""
    bm = ""
    for i,(h,t) in enumerate(rows):
      bh+="{t:moment(%d,'X'), y:%d},"%(int(t/1000), h)
      if not i==0:
        dt = int( (t - rows[i-1][1])/1000)
        db = h-rows[i-1][0]
        bpm = db*60./dt
        bm+="{x:moment(%d,'X'), y:%.1f},"%(int(t/1000), bpm)

    cur.execute("SELECT COUNT(id) from giver_balance")
    rows=cur.fetchone()[0]
    fr = 1
    if rows>100:
      fr = int(rows/40)
    cur.execute("SELECT timestamp, balance from giver_balance where id%%%d=0 order by id"%(fr))
    rows=cur.fetchall()
    bal = ""
    for i,(t, b) in enumerate(rows):
      bal+="{t:moment(%d,'X'), y:%.2f},"%(t, b/1e9)
    return "["+bh+"]", "["+bm+"]", "["+bal+"]"

def insert_giver_balance(timestamp, balance, db_name = "explorer.db"):
  with sqlite3.connect(db_name) as conn:
    cur = conn.cursor()
    cur.execute("INSERT INTO giver_balance (timestamp, balance) VALUES (%d, %d)"%(int(timestamp), int(balance*1e9)))

