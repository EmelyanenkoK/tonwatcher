import json

def read_config():
  with open("db_credents.json", "r") as f:
    jss = f.read()
  jss = jss.replace("\n"," ")
  return json.loads(jss)

def get_psql_credents():
  config = read_config()
  return config['psql']

def get_mongo_credents():
  config = read_config()
  return config['mongo']
