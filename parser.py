class Token:
  pass

class Map(Token):
  def __repr__(self):
    return "MAP(->)"

class Down(Token):

  def __init__(self, to_level=0):
    self.level = to_level

  def __repr__(self):
    return "DOWN(%d)"%self.level
    

class Up(Token):

  def __init__(self, from_level=0):
    self.level = from_level

  def __repr__(self):
    return "UP(%d)"%self.level


class Word(Token):
  def __init__(self, word):
    self.v = word
  def __repr__(self):
    return "WORD(%s)"%self.v
 

class Integer(Token):
  def __init__(self, i):
    self.v = int(i)
  def __repr__(self):
    return "Int(%d)"%self.v
  


symbols = {Down:"(", Up:")", Word:"abcdefghijklmnopqrtsuvwxyzABCDEFGHIJKLMNOPQRTSUVWXYZ_@^-", Integer:"0123456789", Map: ":", None:" \t\n"}

def tok_by_symb(c):
  for i in symbols:
    if c in symbols[i]:
      return i

def get_tokens(s):
  cache = ""
  level = 0
  tokens = []
  state = None
  for c in s:
    next_state = tok_by_symb(c)
    if state in [Word, Integer] and ( (not next_state == state) and not set([state, next_state])==set([Word, Integer]) ):
        tokens.append(state(cache))
        cache = ""
        state = next_state          
    if next_state in [Word, Integer]:
        cache += c
        state = next_state if not (Word in [state, next_state]) else Word
        continue
    elif next_state is Down:      
        level+=1
        tokens.append(Down(level))
        state = None
        continue
    elif next_state is Up:      
        tokens.append(Up(level))
        level-=1
        state = None
        continue
    elif next_state is Map:      
        tokens.append(Map())
        state = None
        continue
    else:
      state = None
      continue
  return tokens

unparsable_entities = ["state_update", "code", "data"]

def build_object(tokens, wait_till_the_end = False, most_top_level = True):
  'returns value, upper k and number of consumed tokens'
  ret = {}
  pass_till_n = None
  key = None
  i=0
  consumed = 0 
  stop_level = None  
  awaiting_value, cur_key = False, None
  while i<len(tokens):
    t = tokens[i]
    consumed+=1
    if isinstance(t, Up):
       if t.level == stop_level:
         if most_top_level:
           break
         else:
           return key, ret, consumed    
       elif wait_till_the_end and t.level>stop_level:
         # generally parser should not see Up token of not his own level
         # since any children expression will be parsed by it's own parser call, 
         # however when we ignore anything inside some expression we should 
         # also ignore all childs
         i+=1
         continue
       else:
         raise "1"
    elif wait_till_the_end and i:
      i+=1
      continue
    if isinstance(t, Down):
       if i==0:
         stop_level = t.level
         i+=1
       else:
         wt = (isinstance(tokens[i-2], Word) and tokens[i-2].v in unparsable_entities)
         k,v,n = build_object(tokens[i:], wt, most_top_level = False)
         if wt:
           k,v = "content", "not parsable"
         if awaiting_value:
           ret[cur_key]={k:v}
           awaiting_value, cur_key = False, None
         elif k:
           ret[k]=v            
         else:
           ret.update(v)
         i+=n
         consumed+=n-1
         continue
    if type(t) in [Word, Integer]:
      if awaiting_value:
          ret[cur_key] = t.v
          awaiting_value, cur_key = False, None
          i+=1
          continue
      elif i+1<len(tokens) and isinstance(tokens[i+1], Map):
            awaiting_value, cur_key = True, t.v
            i+=2
            consumed+=1
            continue
      elif not key:
          key = t.v
          i+=1
          continue
      else:
           print(key, tokens[i-2:i+2])
           raise "2"
  if key: 
    return {key:ret}
  else:
    return ret

def parse(ton_output):
  return build_object(get_tokens(ton_output))
  

