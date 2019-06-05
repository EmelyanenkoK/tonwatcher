import asyncio
import sys
import time
from asyncio.subprocess import PIPE, STDOUT
from aiohttp import web, ClientSession
import aiohttp_jinja2
import jinja2
import logging
import sqlite3
import time
import json
from datetime import datetime
from utils import *
from db import *
from parser import parse


# ===========  CHANGE PARAMS HERE ===========
server_port = 8090
logging_level = logging.DEBUG # one of [logging.CRITICAL, logging.ERROR, logging.INFO, logging.DEBUG]
lite_client_port = 8000
lite_client_host = "http://localhost"

# ===========  END OF PARAMS SECTION ===========  



loop = asyncio.get_event_loop()
ton_logger = logging.getLogger("TON")
explorer_logger = logging.getLogger("Explorer")
logging.basicConfig(level=logging_level, format='%(asctime)s %(name)s %(levelname)s:%(message)s')


async def fetch(session, url):
    async with session.get(url) as response:
        return await response.text()

async def request(method, params=[]):
    async with ClientSession() as session:
        addr = "%s:%s/%s"%(lite_client_host, lite_client_port, method)
        if len(params):
          addr+="/"+"/".join(params)
        result = await fetch(session, addr)
        #TODO it is dangerous
        result = result.replace("'", '"').replace("\n", " ")
        return json.loads(result)["result"]

async def check_testnet_giver_balance():
  giver = "-1:8156775b79325e5d62e742d9b96c30b6515a5cd2f1f64c5da4b193c03f070e0d"
  while True:
      try:
        res = await get_account(giver)
        try:
          insert_giver_balance(time.time(), res["balance"])
        except:
          pass
      except Exception as e:
        explorer_logger.error(e)
      await asyncio.sleep(10) 

def get_prev_block(block_dump):
  root_hash = block_dump["block"]["block"]["info"]["block_info"]["prev_ref"]["prev_blk_info"]["prev"]["ext_blk_ref"]["root_hash"]
  seq_no = block_dump["block"]["block"]["info"]["block_info"]["prev_ref"]["prev_blk_info"]["prev"]["ext_blk_ref"]["seq_no"]
  file_hash = block_dump["block"]["block"]["info"]["block_info"]["prev_ref"]["prev_blk_info"]["prev"]["ext_blk_ref"]["file_hash"]
  hz3 = 8000000000000000
  chain_id = -1
  root_hash = root_hash[1:] #remove 'x'
  file_hash = file_hash[1:] #remove 'x'
  return "(%d,%d,%d):%s:%s"%( int(chain_id), int(hz3), int(seq_no), str(root_hash), str(file_hash) )

   
block_awaiting_list = []
async def get_blocks_routine():
    while True:
      while len(block_awaiting_list):
        full_id = block_awaiting_list.pop()  
        print("getting block %s"%full_id)
        block_dump = await dump_block(full_id)
        block_num = int(block_dump["block"]["block"]["info"]["block_info"]["seq_no"])
        insert_block(block_num, time.time(), full_id)  
        prev = get_prev_block(block_dump)     
        if block_num>1 and not get_block(block_num-1):
            block_awaiting_list.append(prev)        
      await asyncio.sleep(0.3) 
    pass    

async def check_block_routine():
    while True:
      try:
        res = await get_last_block_info()
        try:
          if not get_block(res["height"]):
            block_awaiting_list.append(res["full_id"])
        except Exception as e:
          print(e)
      except Exception as e:
        explorer_logger.error(e)
      await asyncio.sleep(1) 
    pass

async def get_server_time():
    time = await request('time')
    time = datetime.utcfromtimestamp(int(time)).strftime('%Y-%m-%d %H:%M:%S')
    return time

async def get_last_block_info():
    last = await request('last')
    main_chain, keys = last.split(")")
    chain_id, hz3, block_height = main_chain[1:].split(",")
    root_hash, file_hash = keys[1:].split(":")
    return {"height":block_height, "chain_id":chain_id, "root_hash":root_hash, "file_hash":file_hash, "hz3":hz3, "full_id":last}
 
async def dump_block(full_id):
    block = await request('getblock', [full_id])
    block["block"] = parse(block["block"])
    return block


async def get_account(account):
    account = await request('getaccount', [account])
    account["account"] = parse(account["account"])
    try:
      balance = int(account["account"]["account"]["storage"]["account_storage"]["balance"]["currencies"]["grams"]["nanograms"]["amount"]["var_uint"]["value"])/1e9
    except:
      balance = None
    return {"balance":balance, "full_info":json.dumps(account, indent=2)}

@aiohttp_jinja2.template('index.html')
async def handle(request):
    account = None
    try: 
        data = await request.post()
        account = data["account"]
    except:
        pass
    finally:
      if account:
        raise web.HTTPFound('/account/%s'%account)
    time = await get_server_time()
    block_info = await get_last_block_info()
    ret = {"time":time, "block_height":block_info["height"], \
            "root_hash": block_info["root_hash"], "file_hash": block_info["file_hash"],
            "last_block": "Last masterchain block is (chain_id %s : %s : height: %s)"%(block_info["chain_id"], block_info["hz3"], block_info["height"])}
    account = request.match_info.get('account', None)
    if account:
      try:
        account_data = await get_account(account)
        ret["account_info"] = account_data["full_info"]
        ret["balance"] = account_data["balance"]      
      except:
        pass
    else:
      graph_data = get_graph_data()
      ret["block_height_graph_data"] =  graph_data[0]
      ret["block_per_minute_graph_data"] =  graph_data[1]
      ret["giver_balance"] =  graph_data[2]
    return ret


if __name__ == '__main__':
  loop.create_task(check_block_routine())
  loop.create_task(get_blocks_routine())
  loop.create_task(check_testnet_giver_balance())
  app = web.Application(loop=loop)
  app.router.add_get('/', handle)
  app.router.add_post('/account', handle)
  app.router.add_get('/account/{account}', handle)
  aiohttp_jinja2.setup(app,
      loader=jinja2.FileSystemLoader("./"))
  try:
    init_base()
  except sqlite3.OperationalError as e:
    pass
  web.run_app(app, port=server_port)
