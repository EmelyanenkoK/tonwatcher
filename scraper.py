import asyncio
import sys
import time
import logging
import sqlite3
import time
import json
from datetime import datetime
from utils import *
from address_utils import detect_address
from db import *
from ton_api import *
from parser import parse


# ===========  CHANGE PARAMS HERE ===========
logging_level = logging.DEBUG # one of [logging.CRITICAL, logging.ERROR, logging.INFO, logging.DEBUG]

# ===========  END OF PARAMS SECTION ===========  



loop = asyncio.get_event_loop()
scraper_logger = logging.getLogger("Scraper")
logging.basicConfig(level=logging_level, format='%(asctime)s %(name)s %(levelname)s:%(message)s')


async def check_testnet_giver_balance():
  giver = "-1:8156775b79325e5d62e742d9b96c30b6515a5cd2f1f64c5da4b193c03f070e0d"
  while True:
      try:
        res = await get_account(giver)
        try:
          await insert_giver_balance(time.time(), res["balance"])
        except:
          pass
      except Exception as e:
        scraper_logger.error(e)
      await asyncio.sleep(10) 

def get_prev_blocks(block_dump):
  return block_dump["header"]["prev_blocks"]
   
async def get_blocks_routine():
    while True:
      block_awaiting_list = await get_not_downloaded()
      while len(block_awaiting_list):
        full_id = block_awaiting_list.pop(0)
        id_dict = parse_full_id(full_id)
        block_dump = await dump_block(full_id)
        gen_time = int(block_dump["block"]["block"]["info"]["block_info"]["gen_utime"])
        print(json.dumps(block_dump, indent=2))
        await insert_block(id_dict["chain_id"], id_dict["prefix"], id_dict["height"], block_dump)  
        await mark_downloaded(id_dict["chain_id"], id_dict["prefix"], id_dict["height"], gen_time=gen_time)
        prevs = get_prev_blocks(block_dump)  
        prevs.append(block_dump["header"]["reference_masterchain_block"])   
        for prev in prevs:
          prev_id_dict = parse_full_id(prev)
          w, p, h = prev_id_dict["chain_id"], prev_id_dict["prefix"], prev_id_dict["height"]
          if not await has_block_id(w, p, h):
             await add_block_id(w, p, h,  prev_id_dict["root_hash"], prev_id_dict["file_hash"])
      await asyncio.sleep(0.3) 
    pass    

async def check_block_routine():
    while True:
      try:
        res = await get_last_block_info()
        w, p, h = res["chain_id"], res["prefix"], res["height"]
        try:
          if not await has_block_id(w, p, h):
            await add_block_id(w, p, h, res["root_hash"], res["file_hash"])
        except Exception as e:
          print(e)
      except Exception as e:
        scraper_logger.error(e)
      await asyncio.sleep(1) 
    pass

async def check_shards_routine():
    while True:
      try:
        res = await get_last_shards()
        shard_blocks = [ i["block_id"] for i in res["shard_configuration"]["shards_list"]]
        for block in shard_blocks:
          id_dict = parse_full_id(block)
          w, p, h = id_dict["chain_id"], id_dict["prefix"], id_dict["height"]
          try:
            if not await has_block_id(w, p, h):
              await add_block_id(w, p, h, id_dict["root_hash"], id_dict["file_hash"])
          except Exception as e:
            print(e)
      except Exception as e:
        scraper_logger.error(e)
      await asyncio.sleep(20) 
    pass



if __name__ == '__main__':
  loop.create_task(check_block_routine())
  loop.create_task(check_shards_routine())
  loop.create_task(get_blocks_routine())
  loop.create_task(check_testnet_giver_balance())
  loop.run_forever()
