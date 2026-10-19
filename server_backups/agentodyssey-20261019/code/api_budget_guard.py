"""Atomic shared pre-request reservations. No network or provider credentials."""
import json,sqlite3,uuid
from contextlib import contextmanager
from pathlib import Path

class BudgetStopped(RuntimeError):pass
FIELDS=('calls','input_tokens','uncached_input_tokens','output_tokens')
DEFAULT_LIMITS={'calls':80,'input_tokens':2_000_000,'uncached_input_tokens':400_000,'output_tokens':60_000}

class BudgetGuard:
    def __init__(self,path,limits,per_run=None):
        self.path=str(path);Path(path).parent.mkdir(parents=True,exist_ok=True)
        self.limits=dict(limits);self.per_run=dict(per_run or limits)
        assert set(self.limits)==set(FIELDS) and set(self.per_run)==set(FIELDS)
        assert all(isinstance(n,int) and n>0 for n in list(self.limits.values())+list(self.per_run.values()))
        with self.connect() as c:
            c.executescript('CREATE TABLE IF NOT EXISTS config (id INTEGER PRIMARY KEY, value TEXT); CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY, run TEXT, state TEXT, calls INTEGER, input_tokens INTEGER, uncached_input_tokens INTEGER, output_tokens INTEGER, detail TEXT); CREATE TABLE IF NOT EXISTS halt (id INTEGER PRIMARY KEY, reason TEXT);')
            value=json.dumps([self.limits,self.per_run],sort_keys=True)
            c.execute('INSERT OR IGNORE INTO config VALUES(1,?)',(value,))
            assert c.execute('SELECT value FROM config WHERE id=1').fetchone()[0]==value,'Cannot silently increase a persisted budget'
    @contextmanager
    def connect(self):
        c=sqlite3.connect(self.path,timeout=30);c.execute('PRAGMA busy_timeout=30000')
        try:
            with c:yield c
        finally:c.close()
    def usage(self,run=None):
        with self.connect() as c:return self._usage(c,run)
    def _usage(self,c,run=None):
        q='SELECT '+','.join('COALESCE(SUM('+f+'),0)' for f in FIELDS)+' FROM requests';args=()
        if run is not None:q+=' WHERE run=?';args=(run,)
        return dict(zip(FIELDS,c.execute(q,args).fetchone()))
    def reserve(self,run,messages,max_output):
        assert isinstance(run,str) and run and isinstance(max_output,int) and 0<max_output<=768
        assert isinstance(messages,list) and all(isinstance(m.get('content'),str) for m in messages)
        # Conservative byte-based reservation, not an exact DeepSeek tokenizer.
        estimate=len(json.dumps(messages,ensure_ascii=False).encode('utf-8'))+1024+64*len(messages)
        if estimate>160_000:raise BudgetStopped('single_request_input_bound_exceeded')
        amount={'calls':1,'input_tokens':estimate,'uncached_input_tokens':estimate,'output_tokens':max_output}
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            halt=c.execute('SELECT reason FROM halt WHERE id=1').fetchone()
            if halt:raise BudgetStopped('batch_halted: '+halt[0])
            for scope,limit in [(None,self.limits),(run,self.per_run)]:
                used=self._usage(c,scope)
                for f in FIELDS:
                    if used[f]+amount[f]>limit[f]:raise BudgetStopped(('batch' if scope is None else 'run')+'_'+f+'_budget_exceeded')
            rid=uuid.uuid4().hex
            c.execute('INSERT INTO requests VALUES(?,?,?,?,?,?,?,?)',(rid,run,'reserved',*[amount[f] for f in FIELDS],json.dumps({'reservation':amount})))
            return rid
    def complete(self,rid,usage):
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE');r=c.execute('SELECT state,input_tokens,uncached_input_tokens,output_tokens FROM requests WHERE id=?',(rid,)).fetchone()
            assert r and r[0]=='reserved','Unknown or already settled request'
            if not isinstance(usage,dict):usage={}
            prompt=usage.get('prompt_tokens');out=usage.get('completion_tokens')
            miss=usage.get('prompt_cache_miss_tokens',prompt)
            if not all(type(x) is int and x>=0 for x in [prompt,out,miss]) or miss>prompt:
                c.execute('INSERT OR REPLACE INTO halt VALUES(1,?)',('missing_or_invalid_provider_usage',));c.execute('UPDATE requests SET state=? WHERE id=?',('unknown_usage',rid));return False
            c.execute('UPDATE requests SET state=?,input_tokens=?,uncached_input_tokens=?,output_tokens=?,detail=? WHERE id=?',('completed',prompt,miss,out,json.dumps(usage),rid))
            if prompt>r[1] or miss>r[2] or out>r[3]:
                c.execute('INSERT OR REPLACE INTO halt VALUES(1,?)',('provider_usage_exceeded_conservative_reservation',));return False
            return True
    def fail_unknown(self,rid,reason):
        # Timeout can have been billed: retain the full reservation and prevent automatic retry.
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE');c.execute('UPDATE requests SET state=?,detail=? WHERE id=?',('unknown_outcome',str(reason)[:400],rid))
            c.execute('INSERT OR REPLACE INTO halt VALUES(1,?)',('uncertain_request_outcome_no_retry',))

def guarded_generate(guard,run,payload,upstream):
    rid=guard.reserve(run,payload['messages'],payload['max_tokens'])
    try:result=upstream(payload,rid)
    except Exception as e:guard.fail_unknown(rid,type(e).__name__);raise BudgetStopped('upstream_outcome_uncertain; no retry') from e
    usage=result.get('usage') if isinstance(result,dict) else None
    if not guard.complete(rid,usage):raise BudgetStopped('provider_usage_invalid_or_exceeded_reservation; batch halted')
    return result
