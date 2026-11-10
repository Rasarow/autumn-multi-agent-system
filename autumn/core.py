"""Bounded, evidence-first multi-agent workflow. No arbitrary tool execution."""
from __future__ import annotations
import contextlib, hashlib, json, os, re, sqlite3, time, uuid, urllib.request
from pathlib import Path
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

ROOT=Path(__file__).resolve().parents[1]
STOP={'the','a','an','is','are','was','were','what','which','how','to','of','in','for','and','on','does','do','can','you','me','tell','please'}
def words(s): return [w for w in re.findall(r'[a-z0-9]+',s.lower()) if w not in STOP and len(w)>1]
def norm(s): return ' '.join(s.split())

class Telemetry:
    """Local JSONL logs and correlated spans, Prometheus textfile metrics, alerts."""
    def __init__(self, root):
        self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True)
        self.counters={}; self.trace=uuid.uuid4().hex
        existing=self.root/'metrics.prom'
        if existing.exists():
            for line in existing.read_text().splitlines():
                key,value=line.split(); self.counters[key.removeprefix('autumn_')]=float(value)
    def event(self,event_name,**fields):
        record={'timestamp':time.time(),'trace_id':self.trace,'event':event_name,**fields}
        with (self.root/'events.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(record)+'\n')
    def inc(self,name,value=1):
        self.counters[name]=self.counters.get(name,0)+value
        temp=self.root/'metrics.tmp'
        temp.write_text('\n'.join(f'autumn_{k} {v}' for k,v in sorted(self.counters.items()))+'\n')
        temp.replace(self.root/'metrics.prom')
    def alert(self,reason):
        record={'timestamp':time.time(),'trace_id':self.trace,'severity':'warning','reason':reason}
        with (self.root/'alerts.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(record)+'\n')
        self.event('alert',reason=reason); self.inc('alerts_total')
    @contextlib.contextmanager
    def span(self,name):
        start=time.perf_counter(); sid=uuid.uuid4().hex[:16]
        self.event('span_start',span_id=sid,name=name)
        try: yield
        except Exception as e:
            self.inc('errors_total'); self.alert('node_error:'+name)
            self.event('span_error',span_id=sid,error_type=type(e).__name__); raise
        finally:
            duration=time.perf_counter()-start
            self.event('span_end',span_id=sid,name=name,duration_s=duration)
            if duration>30: self.alert('slow_node:'+name)

class Memory:
    def __init__(self,path):
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(path); self.db.row_factory=sqlite3.Row
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS sections(id TEXT PRIMARY KEY, title TEXT, body TEXT,
          valid_from TEXT, valid_to TEXT, sha256 TEXT);
        CREATE VIRTUAL TABLE IF NOT EXISTS search USING fts5(id UNINDEXED,title,body);
        CREATE TABLE IF NOT EXISTS episodes(id TEXT PRIMARY KEY,session TEXT,question TEXT,
          result TEXT,status TEXT,created REAL);
        """)
    def ingest(self,folder):
        # One atomic replacement removes deleted sections and avoids stale FTS rows.
        docs=[]
        for file in sorted(Path(folder).glob('*.md')):
            if file.is_symlink(): raise ValueError('symlink_document')
            if file.stat().st_size>100000: raise ValueError('document_too_large')
            text=file.read_text(encoding='utf-8'); meta,body=text.split('\n---\n',1)
            fields=dict(line.split(': ',1) for line in meta.splitlines() if ': ' in line)
            docs.append((fields['id'],fields['title'],body.strip(),fields['valid_from'],fields.get('valid_to',''),hashlib.sha256(body.encode()).hexdigest()))
        with self.db:
            self.db.execute('DELETE FROM sections'); self.db.execute('DELETE FROM search')
            self.db.executemany('INSERT INTO sections VALUES(?,?,?,?,?,?)',docs)
            self.db.executemany('INSERT INTO search VALUES(?,?,?)',[(r[0],r[1],r[2]) for r in docs])
        return len(docs)
    def search_documents(self,query,as_of,limit=4):
        tokens=list(dict.fromkeys(words(query)))[:20]
        if not tokens: return []
        expression=' OR '.join('"'+t+'"' for t in tokens)
        return [dict(r) for r in self.db.execute("""
          SELECT s.*,bm25(search) AS score FROM search JOIN sections s ON s.id=search.id
          WHERE search MATCH ? AND s.valid_from<=? AND (s.valid_to='' OR s.valid_to>?)
          ORDER BY score LIMIT ?""",(expression,as_of,as_of,min(limit,4)))]
    def read_section(self,identifier,as_of):
        if not re.fullmatch(r'[A-Z0-9_-]{1,48}',identifier): raise ValueError('invalid_section_id')
        r=self.db.execute("SELECT * FROM sections WHERE id=? AND valid_from<=? AND (valid_to='' OR valid_to>?)",(identifier,as_of,as_of)).fetchone()
        if r is None: raise KeyError('section_not_found')
        return dict(r)
    def recall(self,session,as_of=None):
        # Only approved episodes return; provenance remains attached to every result.
        return [dict(r) for r in self.db.execute("SELECT question,result FROM episodes WHERE session=? AND status='approved' AND (? IS NULL OR json_extract(result,'$.as_of')=?) ORDER BY created DESC LIMIT 3",(session,as_of,as_of))]
    def save(self,session,question,result,status):
        with self.db: self.db.execute('INSERT INTO episodes VALUES(?,?,?,?,?,?)',(uuid.uuid4().hex,session,question,json.dumps(result),status,time.time()))
    def forget(self,session):
        with self.db: self.db.execute('DELETE FROM episodes WHERE session=?',(session,))

PLAN_SCHEMA={'type':'object','properties':{'query':{'type':'string'},'complex':{'type':'boolean'}},'required':['query','complex'],'additionalProperties':False}
DRAFT_SCHEMA={'type':'object','properties':{'abstain':{'type':'boolean'},'claims':{'type':'array','maxItems':4,'items':{'type':'object','properties':{'source_id':{'type':'string'},'quote':{'type':'string'}},'required':['source_id','quote'],'additionalProperties':False}}},'required':['abstain','claims'],'additionalProperties':False}
# Select evidence before deciding abstention. In local tests the reverse order
# biased constrained decoding toward false abstention, despite valid evidence.
DRAFT_SCHEMA['properties']={k:DRAFT_SCHEMA['properties'][k] for k in ['claims','abstain']}
VERIFY_SCHEMA={'type':'object','properties':{'approved':{'type':'boolean'},'reason':{'type':'string'}},'required':['approved','reason'],'additionalProperties':False}

class LLMClient:
    def __init__(self,config,telemetry): self.config=config; self.t=telemetry; self.calls=0
    def ask(self,tier,system,payload,schema):
        self.calls+=1
        if self.calls>5: raise RuntimeError('model_call_budget_exceeded')
        target=self.config['models'][tier]
        request={'model':target['name'],'messages':[{'role':'system','content':system},{'role':'user','content':json.dumps(payload)}],
          'temperature':0,'seed':42,'max_tokens':500,'chat_template_kwargs':{'enable_thinking':False},
          'response_format':{'type':'json_schema','json_schema':{'name':'result','strict':True,'schema':schema}}}
        data=json.dumps(request).encode(); start=time.perf_counter()
        req=urllib.request.Request(target['url']+'/v1/chat/completions',data=data,headers={'Content-Type':'application/json'})
        # Retries are deliberately absent: repair is bounded at workflow level.
        with urllib.request.urlopen(req,timeout=60) as r: result=json.load(r)
        content=result['choices'][0]['message']['content']
        self.t.inc('llm_calls_total'); self.t.inc('completion_tokens_total',result.get('usage',{}).get('completion_tokens',0))
        self.t.event('llm',tier=tier,model=target['name'],duration_s=time.perf_counter()-start,usage=result.get('usage',{}))
        if result['choices'][0].get('finish_reason')=='length': raise ValueError('truncated_model_output')
        return json.loads(content)

def validate_draft(draft,evidence):
    if not isinstance(draft,dict) or type(draft.get('abstain')) is not bool or not isinstance(draft.get('claims'),list): return False,'bad_schema'
    if draft['abstain']: return not draft['claims'],'abstain'
    if not 1<=len(draft['claims'])<=4: return False,'empty_or_excess_claims'
    sources={e['id']:e['body'] for e in evidence}
    for c in draft['claims']:
        if not isinstance(c,dict) or not isinstance(c.get('quote'),str): return False,'bad_claim'
        q=norm(c['quote'])
        if len(q)<12 or c.get('source_id') not in sources: return False,'unknown_citation'
        if q not in norm(sources[c['source_id']]): return False,'unsupported_quote'
    return True,'quotes_match'

class State(TypedDict,total=False):
    question:str; as_of:str; session:str; history:list; query:str; tier:str; evidence:list
    draft:dict; approved:bool; reason:str; repairs:int; result:dict

def run(question,config=None,memory=None,client=None,telemetry=None,session='demo',as_of='2026-11-10'):
    if not isinstance(question,str) or not 1<=len(question)<=2000: raise ValueError('question_length')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',as_of): raise ValueError('invalid_date')
    from datetime import date
    date.fromisoformat(as_of)
    config=config or json.loads((ROOT/'config.json').read_text())
    base=Path(os.environ.get('AUTUMN_STATE',ROOT/'state'))
    t=telemetry or Telemetry(base/'telemetry'); t.trace=uuid.uuid4().hex
    m=memory or Memory(base/'memory.db')
    if not m.db.execute('SELECT count(*) FROM sections').fetchone()[0]: m.ingest(ROOT/'data')
    c=client or LLMClient(config,t)
    prompts={k:(ROOT/'prompts'/f'{k}.md').read_text() for k in ['planner','writer','verifier']}
    skills={k:(ROOT/'skills'/k/'SKILL.md').read_text() for k in ['evidence_search','grounded_answer','verify_evidence']}
    soul=(ROOT/'SOUL.md').read_text()
    def planner(s):
        with t.span('planner'):
            p=c.ask('small',prompts['planner']+'\n'+soul+'\n'+skills['evidence_search'],{'question':s['question'],'as_of':s['as_of'],'recent_verified_history':s['history']},PLAN_SCHEMA)
            if not isinstance(p.get('query'),str) or not p['query'].strip() or len(p['query'])>400: raise ValueError('invalid_search_query')
            # Budget guard can escalate a small model's optimistic complexity judgment.
            complex_request=any(x in s['question'].lower() for x in ['compare','why','both','before','after','changed']) or (bool(p.get('complex')) and len(words(s['question']))>10)
            tier='large' if complex_request else 'medium'
            t.event('route',tier=tier,planner_complex=bool(p.get('complex')),reason='complexity_and_budget_policy')
            return {'query':s['question']+' '+p['query'],'tier':tier}
    def researcher(s):
        with t.span('researcher'):
            hits=m.search_documents(s['query'],s['as_of'])
            evidence=[m.read_section(h['id'],s['as_of']) for h in hits]
            t.inc('retrievals_total'); t.event('retrieval',source_ids=[e['id'] for e in evidence])
            return {'evidence':evidence}
    def writer(s):
        with t.span('writer'):
            tier='large' if s['repairs'] else s['tier']
            temporal_contract=f"\nThe authoritative effective date for this request is {s['as_of']}. Every supplied source passed the validity filter for this date. A later expiry does not invalidate evidence on this date."
            evidence_view=[{'id':e['id'],'body':e['body'],'valid_at':s['as_of']} for e in s['evidence']]
            draft=c.ask(tier,prompts['writer']+'\n'+skills['grounded_answer']+temporal_contract,{'question':f"On {s['as_of']}: {s['question']}",'as_of':s['as_of'],'untrusted_evidence':evidence_view,'previous_failure':s.get('reason','')},DRAFT_SCHEMA)
            return {'draft':draft}
    def verifier(s):
        with t.span('verifier'):
            valid,reason=validate_draft(s['draft'],s['evidence'])
            if not valid: return {'approved':False,'reason':reason}
            if s['draft']['abstain']: return {'approved':False,'reason':'no_supported_answer'}
            verdict=c.ask('large',prompts['verifier']+'\n'+skills['verify_evidence']+f"\nThe authoritative effective date is {s['as_of']}. Sources were filtered for that date.",{'question':s['question'],'as_of':s['as_of'],'untrusted_evidence':s['evidence'],'candidate':s['draft']},VERIFY_SCHEMA)
            approved=verdict.get('approved') is True
            return {'approved':approved,'reason':str(verdict.get('reason',''))[:300]}
    def repair(s):
        t.inc('repairs_total'); t.event('repair',reason=s['reason']); return {'repairs':s['repairs']+1}
    def finish(s):
        status='approved' if s['approved'] else 'abstained'
        result={'status':status,'question':s['question'],'as_of':s['as_of'],'trace_id':t.trace,
          'claims':s['draft']['claims'] if s['approved'] else [],'reason':s['reason'],'repairs':s['repairs']}
        if not s['approved']: t.alert('answer_withheld')
        m.save(s['session'],s['question'],result,status); t.inc('requests_total'); t.inc(status+'_total')
        t.event('workflow_end',status=status); return {'result':result}
    g=StateGraph(State)
    for name,fn in [('planner',planner),('researcher',researcher),('writer',writer),('verifier',verifier),('repair',repair),('finish',finish)]: g.add_node(name,fn)
    g.add_edge(START,'planner'); g.add_edge('planner','researcher'); g.add_edge('researcher','writer'); g.add_edge('writer','verifier')
    g.add_conditional_edges('verifier',lambda s:'finish' if s['approved'] or s['repairs']>=1 or s['reason']=='no_supported_answer' else 'repair')
    g.add_edge('repair','writer'); g.add_edge('finish',END)
    start=time.perf_counter()
    try:
        result=g.compile().invoke({'question':question,'as_of':as_of,'session':session,'history':m.recall(session,as_of),'repairs':0},{'recursion_limit':12})['result']
    except Exception as e:
        t.alert('workflow_failed_closed'); t.inc('failed_total')
        result={'status':'error','claims':[],'reason':type(e).__name__,'trace_id':t.trace}
    elapsed=time.perf_counter()-start; t.inc('request_seconds_sum',elapsed)
    result['elapsed_s']=round(elapsed,3)
    return result
