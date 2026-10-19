"""Explicit 500-step protocol: same atomic guard, larger single-request byte bound."""
import json,uuid
from api_budget_guard import BudgetGuard as OriginalGuard,BudgetStopped,FIELDS,guarded_generate
class BudgetGuard(OriginalGuard):
    def reserve(self,run,messages,max_output):
        assert isinstance(run,str) and run and isinstance(max_output,int) and 0<max_output<=768
        assert isinstance(messages,list) and all(isinstance(m.get('content'),str) for m in messages)
        estimate=len(json.dumps(messages,ensure_ascii=False).encode('utf-8'))+1024+64*len(messages)
        if estimate>1_000_000:raise BudgetStopped('full_protocol_single_request_input_bound_exceeded')
        amount={'calls':1,'input_tokens':estimate,'uncached_input_tokens':estimate,'output_tokens':max_output}
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE');halt=c.execute('SELECT reason FROM halt WHERE id=1').fetchone()
            if halt:raise BudgetStopped('batch_halted: '+halt[0])
            for scope,limit in [(None,self.limits),(run,self.per_run)]:
                used=self._usage(c,scope)
                for field in FIELDS:
                    if used[field]+amount[field]>limit[field]:raise BudgetStopped(('batch' if scope is None else 'run')+'_'+field+'_budget_exceeded')
            rid=uuid.uuid4().hex;c.execute('INSERT INTO requests VALUES(?,?,?,?,?,?,?,?)',(rid,run,'reserved',*[amount[f] for f in FIELDS],json.dumps({'reservation':amount})));return rid
