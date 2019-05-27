import re
import asyncio
import sys
import time
from asyncio.subprocess import PIPE, STDOUT
from aiohttp import web
import aiohttp_jinja2
import jinja2
import logging
from datetime import datetime

loop = asyncio.get_event_loop()
task_list = []
ton_logger = logging.getLogger("TON")
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s %(levelname)s:%(message)s')

def remove_color(s):
  ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
  return ansi_escape.sub('', s)


async def get_result(readliner, timeout):
  res = ""
  while True:
        try:
            line = await asyncio.wait_for(readliner(), timeout)
            line = remove_color(line.decode('utf-8'))
        except asyncio.TimeoutError:
            pass
        else:
            if not line:
                break
            else: 
                res+=line
                continue 
        break
  return res




async def run_command(*args, timeout=0.2, initial_timeout=5):
    process = await asyncio.create_subprocess_exec(*args,
            stdin=PIPE, stdout=PIPE, stderr=STDOUT)
    time.sleep(initial_timeout)
    #initialisation
    ton_logger.info("initialisation of ton client...")
    output = await get_result(process.stdout.readline, timeout)
    if len(output):
      ton_logger.info("Successfully initialised")
    while True:
        if not len(task_list):
          await asyncio.sleep(0.1)        
          continue
        while len(task_list):
          task, future, params = task_list.pop()
          ton_logger.info("Processing %s request %s"%(task, str(params) if params else ''))
          if task in ["last", "time"]:
            process.stdin.write(task.encode("utf-8")+b"\n")
            await process.stdin.drain()
            ton_logger.debug("Awaiting result")
            output = await get_result(process.stdout.readline, timeout)
            ton_logger.debug("Got result")
            future.set_result(output)
          if task in ["getaccount"]:
            process.stdin.write((task+" "+params[0]).encode("utf-8") + b"\n")
            await process.stdin.drain()
            ton_logger.debug("Awaiting result")
            output = await get_result(process.stdout.readline, timeout)
            ton_logger.debug("Got result")
            future.set_result(output)

    return await process.wait()

async def get_server_time():
    time_future = asyncio.Future()
    task_list.append(('time',time_future, None))
    res = await time_future
    time = int(res[res.find("server time is")+len("server time is"):])
    time = datetime.utcfromtimestamp(time).strftime('%Y-%m-%d %H:%M:%S')
    return time

async def get_last_block_info():
    block_info_future = asyncio.Future()
    task_list.append(('last',block_info_future, None))
    res = await block_info_future
    block_info = (res[res.find("last masterchain block is")+len("last masterchain block is"):]).strip()
    main_chain, keys = block_info.split(")")
    chain_id, hz3, block_height = main_chain[1:].split(",")
    hz1, hz2 = keys[1:].split(":")
    return {"height":block_height, "chain_id":chain_id, "hz1":hz1, "hz2":hz2, "hz3":hz3}


async def get_account(account):
    account_future = asyncio.Future()
    task_list.append(('getaccount',account_future, [account]))
    res = await account_future
    try:
      res=res[res.find("account state is ")+len("account state is "):]
    except:
      pass
    try:
      from_grams = res[res.find("nanograms"):]
      val_start = from_grams.find("value:")+6
      val_finish = from_grams[val_start:].find(")")
      balance = int(from_grams[val_start:val_start+val_finish])/1e9
    except Exception as e:
      balance = 0
    return {"balance":balance, "full_info":res}

@aiohttp_jinja2.template('index.html')
async def handle(request):
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
    return ret


if __name__ == '__main__':
  loop.create_task(run_command("/root/liteclient-build/test-lite-client", "-C", "/root/liteclient-build/ton-lite-client-test1.config.json",))
  app = web.Application(loop=loop)
  app.router.add_get('/', handle)
  app.router.add_get('/account/{account}', handle)
  app.router.add_static('/favicon.ico',"./favicon.ico")
  aiohttp_jinja2.setup(app,
      loader=jinja2.FileSystemLoader("./"))
  web.run_app(app)
