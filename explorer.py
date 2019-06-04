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
        print(addr)
        result = await fetch(session, addr)
        #TODO it is dangerous
        result = result.replace("'", '"').replace("\n", " ")
        print(result)
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
  

async def check_block_routine():
    while True:
      try:
        res = await get_last_block_info()
        try:
          insert_block(res["height"],time.time(), res["hz1"]+":"+res["hz2"] )
        except:
          pass
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
    hz1, hz2 = keys[1:].split(":")
    return {"height":block_height, "chain_id":chain_id, "hz1":hz1, "hz2":hz2, "hz3":hz3}


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
            "unknown_key1": block_info["hz1"], "unknown_key2": block_info["hz2"],
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
