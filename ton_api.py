from aiohttp import ClientSession
import json
from datetime import datetime
from parser import parse
import logging

ton_logger = logging.getLogger("TON")

lite_client_port = 8000
lite_client_host = "http://localhost"

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
        result = json.loads(result)
        if "result" in result:
          return True, result["result"]
        else:
          return False, result["error"]

async def get_server_time():
    res, time = await request('time')
    if not res:
      return "Unknown"
    time = datetime.utcfromtimestamp(int(time)).strftime('%Y-%m-%d %H:%M:%S')
    return time

def parse_full_id(full_id):
    main_chain, keys = full_id.split(")")
    chain_id, prefix, block_height = main_chain[1:].split(",")
    root_hash, file_hash = keys[1:].split(":")
    chain_id, block_height = int(chain_id), int(block_height)
    return {"height":block_height, "chain_id":chain_id, "root_hash":root_hash, "file_hash":file_hash, "prefix":prefix, "full_id":full_id}

def parse_short_id(short_id, with_brackets=True):
    if with_brackets:
      assert "("==short_id[0] and ")"==short_id[-1]
      short_id = short_id[1:-1]
    chain_id, prefix, block_height = short_id.split(",")
    chain_id, block_height = int(chain_id), int(block_height)
    return {"height":block_height, "chain_id":chain_id, "prefix":prefix}


async def get_last_block_info():
    res, last = await request('last')
    if not res:
      u="unknown"
      return {"height":u, "chain_id":u, "root_hash":u, "file_hash":u, "prefix":u, "full_id":u}
    return parse_full_id(last)

async def get_last_shards():
    res, shards = await request('shards')
    if not res:
      raise Exception("Can't get shards")
    shards["shard_configuration"]["shards_info"] = parse(shards["shard_configuration"]["shards_info"])
    return shards
 
async def dump_block(full_id):
    res, block = await request('getblock', [full_id])
    if not res:
      raise Exception(block)
    block["block"] = parse(block["block"])
    return block



async def get_account(account):
    res, account = await request('getaccount', [account])
    if not res:
      return {"balance":None, "full_info":account}
    account["account"] = parse(account["account"])
    try:
      balance = int(account["account"]["account"]["storage"]["account_storage"]["balance"]["currencies"]["grams"]["nanograms"]["amount"]["var_uint"]["value"])/1e9
    except:
      balance = None
    return {"balance":balance, "full_info":json.dumps(account, indent=2), "json_account":account}

async def get_header_footer_data():
    time = await get_server_time()
    block_info = await get_last_block_info()
    ret = {"time":time, "block_height":block_info["height"], \
            "root_hash": block_info["root_hash"], "file_hash": block_info["file_hash"],
            "last_block": "Last masterchain block is (chain_id %s : %s : height: %s)"%(block_info["chain_id"], block_info["prefix"], block_info["height"])}
    return ret
