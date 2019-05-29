import re, asyncio

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


