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
from address_utils import detect_address
from db import *
from ton_api import *
from parser import parse


# ===========  CHANGE PARAMS HERE ===========
server_port = 8080
logging_level = logging.DEBUG # one of [logging.CRITICAL, logging.ERROR, logging.INFO, logging.DEBUG]
lite_client_port = 8000
lite_client_host = "http://localhost"

# ===========  END OF PARAMS SECTION ===========  



loop = asyncio.get_event_loop()
ton_logger = logging.getLogger("TON")
explorer_logger = logging.getLogger("Explorer")
logging.basicConfig(level=logging_level, format='%(asctime)s %(name)s %(levelname)s:%(message)s')

async def get_header_footer_data():
    time = await get_server_time()
    block_info = await get_last_block_info()
    ret = {"time":time, "block_height":block_info["height"], \
            "root_hash": block_info["root_hash"], "file_hash": block_info["file_hash"],
            "last_block": "Last masterchain block is (chain_id %s : %s : height: %s)"%(block_info["chain_id"], block_info["prefix"], block_info["height"])}
    return ret


def is_int(smth):
  try:
    int(smth)
    return True
  except:
    return False

def is_short_block_id(smth, bracket=True):
  try:
    parse_short_id(smth, with_brackets=bracket)
    return True
  except:
    return False

def is_full_block_id(smth, bracket=True):
  try:
    parse_full_id(smth)
    return True
  except:
    return False

@aiohttp_jinja2.template('html_templates/index.html')
async def handle_main(request):
    ret = await get_header_footer_data()
    graph_data = await get_graph_data()
    ret["block_height_graph_data"] =  graph_data[0]
    ret["block_per_minute_graph_data"] =  graph_data[1]
    ret["giver_balance"] =  graph_data[2]
    return ret


@aiohttp_jinja2.template('html_templates/account.html')
async def handle_account(request):
    ret = await get_header_footer_data()
    account = request.match_info.get('account', None)
    try:
        account_data = await get_account(account)
        ret["account_info"] = account_data["full_info"]
        ret["balance"] = account_data["balance"]
        ret["seq_no"] = parse_seq_no(account_data["json_account"])
        ret["contract_type"] = parse_contract_type(account_data["json_account"])
        ret["contract_state"] = parse_contract_state(account_data["json_account"])
        ret["workchain"] = parse_workchain(account_data["json_account"])
    except Exception as e:
        print(e)
    return ret

@aiohttp_jinja2.template('html_templates/index.html')
async def handle_search(request):
    query = ""
    try: 
        data = await request.post()
        query = data["query"].strip()
    except:
        raise web.HTTPFound('/unknown/%s'%query)

    if is_int(query):
          raise web.HTTPFound('/block/(-1,8000000000000000,%d)'%int(query))
    elif is_short_block_id(query, True):
          raise web.HTTPFound('/block/%s'%query)
    elif is_short_block_id(query, False):
          raise web.HTTPFound('/block/(%s)'%query)
    elif is_full_block_id(query):
          short_id = query.split(":")[0]
          raise web.HTTPFound('/block/%s'%short_id)
    elif detect_address(query):
          raise web.HTTPFound('/account/%s'%str(detect_address(query)["raw_form"]))
    raise web.HTTPFound('/unknown/%s'%query)

@aiohttp_jinja2.template('unknown.html')
async def handle_unknown(request):
  query = request.match_info.get('query', None)
  ret = await get_header_footer_data()
  ret["query"] = query
  return ret


@aiohttp_jinja2.template('html_templates/block.html')
async def handle_block(request):
    height = None
    short_id = request.match_info.get('short_id', None)
    ret = await get_header_footer_data()
    try:
      id_dict = parse_short_id(short_id)
      w, p, h = id_dict["chain_id"], id_dict["prefix"], id_dict["height"]
      block_data = await get_block(w, p, h)
      block_data.pop("_id")
      ret["block_data"] = json.dumps(block_data, indent=2)
    except Exception as e:
      ret["block_data"] = "Block is not downloaded yet"
    return ret


if __name__ == '__main__':
  app = web.Application(loop=loop)
  app.router.add_get('/', handle_main)
  app.router.add_post('/search', handle_search)
  app.router.add_get('/unknown/{query}', handle_unknown)
  app.router.add_get('/account/{account}', handle_account)
  app.router.add_get('/block/{short_id}', handle_block)
  aiohttp_jinja2.setup(app,
      loader=jinja2.FileSystemLoader("./"))
  web.run_app(app, port=server_port)
