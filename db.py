import sqlite3

def init_base(db_name = "explorer.db"):
  with sqlite3.connect(db_name) as conn:
    cur = conn.cursor()
    cur.execute("CREATE TABLE blocks(height integer PRIMARY KEY, hash text, timestamp integer)")


def insert_block(height, timestamp, long_hash, db_name = "explorer.db"):
  with sqlite3.connect(db_name) as conn:
    cur = conn.cursor()
    cur.execute("INSERT INTO blocks VALUES (%d, '%s', %d)"%(int(height), long_hash, int(timestamp*1000)))

def get_graph_data(db_name = "explorer.db"):
  with sqlite3.connect(db_name) as conn:
    cur = conn.cursor()
    cur.execute("SELECT COUNT(height) from blocks")
    rows=cur.fetchone()[0]
    fr = 1
    if rows>100:
      fr = int(rows/40)
    print(fr)
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
    return "["+bh+"]", "["+bm+"]"
