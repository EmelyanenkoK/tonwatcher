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


def parse_seq_no(account):
  try:
    print(account)
    data = account["account"]["account"]["storage"]["account_storage"]["state"]['account_active']['data']['just']['value']['raw@^Cell']
    print(data)
    cells = data.split()
    inner_data = cells[2]
    assert inner_data[:2]=="x{" and inner_data[-1]=="}"
    inner_data = inner_data[2:-1]
    seq_no = int(inner_data[:8],16)
    return seq_no
  except Exception as e:
    print(e)
    return 'unknown'



known_contracts = {"FF0020DDA4F260810200D71820D70B1FED44D0D31FD3FFD15112BAF2A122F901541044F910F2A2F80001D31F3120D74A96D307D402FB00DED1A4C8CB1FCBFFC9ED54":"standart wallet", "FF0020DDA4F260D31F01ED44D0D31FD166BAF2A1F80001D307D4D1821804A817C80073FB0201FB00A4C8CB1FC9ED54":"test giver"}
def parse_contract_type(account):
  try:
    data = account["account"]["account"]["storage"]["account_storage"]["state"]['account_active']['code']['just']['value']['raw@^Cell']
    cells = data.split()
    inner_code = cells[2]
    assert inner_code[:2]=="x{" and inner_code[-1]=="}"
    inner_code = inner_code[2:-1]
    return known_contracts.get(inner_code.upper(), 'unknown contract')
  except Exception as e:
    print(e)
    return 'unknown contract'  

def parse_contract_state(account):
  try:
    if 'account_active' in account["account"]["account"]["storage"]["account_storage"]["state"]:
      return 'active account'
    elif 'account_uninit' in account["account"]["account"]["storage"]["account_storage"]["state"]:
      return 'unitialised account'
    raise NotImplemented()
  except Exception as e:
    print(e)
    return 'unknown state'

def parse_workchain(account):
  try:
    workchain_id = account["account"]["account"]["addr"]["addr_std"]["workchain_id"]
    return {'-1':"masterchain (id:-1)", '0': "basechain (id:0)"}.get(str(workchain_id), str(workchain_id))
  except Exception as e:
    print(e)
    return 'unknown workchain'
