import asyncpg
import motor.motor_asyncio as motor
import asyncio


from db_utils import get_psql_credents, get_mongo_credents
'''
PSQL schema
CREATE TABLE blocks (id serial UNIQUE, height integer, workchain integer, prefix varchar(16), root_hash varchar(64), file_hash varchar(64), downloaded int, gen_time bigint, PRIMARY KEY (height, prefix, workchain) );
CREATE TABLE giver_balance (id serial UNIQUE, timestamp bigint, balance bigint);
'''

psql_pool = None
mongo_db = None

def get_mongo_db():
  global mongo_db
  credents = get_mongo_credents()
  uri = "mongodb://%(user)s:%(password)s@%(host)s:%(port)s/%(database)s"%credents
  mongo_client = motor.AsyncIOMotorClient(uri)
  mongo_db = mongo_client[credents["database"]]

get_mongo_db()

async def get_psql_connection():
  global psql_pool
  credents = get_psql_credents()
  psql_pool = await asyncpg.create_pool(host=credents["host"],\
                                    database=credents["database"], \
                                    user=credents["user"], \
                                    password=credents["password"])

def ensure_pool(f):
  async def wrapper(*args, **kwargs):
    if not psql_pool:
      await get_psql_connection()
    return await f(*args, **kwargs)
  return wrapper

@ensure_pool
async def add_block_id(workchain, prefix, height, root_hash, file_hash, downloaded = False):
  async with psql_pool.acquire() as conn:
    await conn.execute("""INSERT INTO blocks 
                           (height, workchain, prefix, root_hash, file_hash, downloaded) 
                          VALUES
                           ($1, $2, $3, $4, $5, $6)
                       """,
                       height, workchain, prefix, root_hash, file_hash, downloaded)

@ensure_pool
async def has_block_id(workchain, prefix, height):
  async with psql_pool.acquire() as psql_conn:
    records =  await psql_conn.fetch("""SELECT height from blocks where height=$1 and prefix=$2 and workchain=$3""",
               height, prefix, workchain)
    return len(records)

@ensure_pool
async def mark_downloaded(workchain, prefix, height, gen_time=None):
  async with psql_pool.acquire() as psql_conn:
    if gen_time:
      await psql_conn.execute("""UPDATE blocks set downloaded=1, gen_time = $4 where height=$1 and prefix=$2 and workchain=$3""", height, prefix, workchain, gen_time)
    else:
      await psql_conn.execute("""UPDATE blocks set downloaded=1 where height=$1 and prefix=$2 and workchain=$3""", height, prefix, workchain)

@ensure_pool
async def get_not_downloaded(n=10):
  async with psql_pool.acquire() as psql_conn:
    records =  await psql_conn.fetch("""SELECT (height, workchain, prefix, root_hash, file_hash) from blocks where downloaded=0 LIMIT $1""", n)
    blocks = []
    for r in records:
      r=r["row"]
      blocks.append("(%s,%s,%s):%s:%s"%(r[1], r[2], r[0], r[3], r[4]))
    return blocks

@ensure_pool
async def get_blocks_by_height(height):
  async with psql_pool.acquire() as psql_conn:
    records =  await psql_conn.fetch("""SELECT (height, workchain, prefix, root_hash, file_hash) from blocks where height=$1""", height)
    blocks = []
    for r in records:
      r=r["row"]
      blocks.append("(%s,%s,%s):%s:%s"%(r[1], r[2], r[0], r[3], r[4]))
    return blocks


async def get_block(workchain, prefix, height):
  return await mongo_db.blocks.find_one({'workchain': workchain, 'prefix': prefix, 'height':height})

async def insert_block(workchain, prefix, height, block):
  block['workchain'] = workchain
  block['prefix'] = prefix
  block['height'] = height
  return await mongo_db.blocks.insert_one(block)

@ensure_pool
async def get_graph_data():
 async with psql_pool.acquire() as psql_conn:
  res = await psql_conn.fetchrow("SELECT COUNT(height) from blocks where gen_time>0")
  print(res)
  rows=res["count"]
  fr = 1
  if rows>100:
    fr = int(rows/40)
  res = await psql_conn.fetch("SELECT height, gen_time from blocks where height%$1=0 and gen_time>0 order by height", fr)
  for r in res:
    print(r, list(r))
  rows = [list(r) for r in res]
  bh = ""
  bm = ""
  for i,(h,t) in enumerate(rows):
    bh+="{t:moment(%d,'X'), y:%d},"%(int(t/1000), h)
    if not i==0:
      dt = int( (t - rows[i-1][1])/1000)
      db = h-rows[i-1][0]
      bpm = db*60./dt
      bm+="{x:moment(%d,'X'), y:%.1f},"%(int(t/1000), bpm)
  res = await psql_conn.fetchrow("SELECT COUNT(id) from giver_balance")
  rows=res["count"]
  fr = 1
  if rows>100:
    fr = int(rows/40)
  res = await psql_conn.fetch("SELECT timestamp, balance from giver_balance where id%$1=0 order by id",fr)
  for r in res:
    print(r)
  rows = [list(r) for r in res]
  bal = ""
  for i,(t, b) in enumerate(rows):
    bal+="{t:moment(%d,'X'), y:%.2f},"%(t, b/1e9)
  return "["+bh+"]", "["+bm+"]", "["+bal+"]"

@ensure_pool
async def insert_giver_balance(timestamp, balance):
  async with psql_pool.acquire() as psql_conn:
    await psql_conn.execute("INSERT INTO giver_balance (timestamp, balance) VALUES ($1, $2)", int(timestamp), int(balance*1e9))

