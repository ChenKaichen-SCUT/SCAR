"""Zero-API integration replay of final safeguards against frozen paid traces.

Every requested prompt must match its recorded hash; no response may be unused.
This checks trace compatibility, not an independent game performance replicate.
"""
import argparse,contextlib,hashlib,json,sys,time
from pathlib import Path
from scar_public.run import build_agent
from scar_public.action_history import historical_intents


class RecordedProvider:
    model='deepseek-flash'
    def generate(self,user_prompt,system_prompt):
        assert self.calls,'Final code requested an unrecorded LLM call'
        c=self.calls.pop(0)
        assert hashlib.sha256((system_prompt+'\0'+user_prompt).encode()).hexdigest()==c['prompt_sha256']
        return dict(response=c['response'],num_input_tokens=c['input_tokens'],num_output_tokens=c['output_tokens'])


def semantic_decision(value):
    # Runtime instrumentation varies even when every decision/certificate matches.
    if isinstance(value,dict):return {k:semantic_decision(v) for k,v in value.items() if k!='compute_and_assembly_ms'}
    if isinstance(value,list):return [semantic_decision(v) for v in value]
    return value


def main():
    from scar.environment import restore
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();results=[]
    for game in ('metropolis','remnant'):
        pair=a.root/'pairs_v3'/game;manifest=json.loads((pair/'manifest.json').read_text());cp=Path(manifest['checkpoint'])
        for arm in ('observe','execute'):
            env=restore(cp/'environment.pkl',a.root/'replay_scratch'/game/arm);provider=RecordedProvider()
            agent=build_agent('action_repair_v14',env,provider);saved=json.loads((cp/'agent.json').read_text())
            saved.update(historical_intents(cp));agent.notebook.load(saved)
            c=agent.resource_controller;c.action_mode=arm;c.mode='structured';c.context_scope=manifest['context_scope']
            times=[];count=0
            for path in sorted((pair/arm/'trace').glob('*.json')):
                row=json.loads(path.read_text());provider.calls=list(row['provider_calls']);provider.step=row['step']-1;start=time.perf_counter()
                with contextlib.redirect_stdout(sys.stderr):
                    action,_,_,response=agent.act(dict(text=row['observation'],step=row['step']-1))
                times.append(time.perf_counter()-start)
                assert not provider.calls,('Unused recorded response',game,arm,row['step'])
                assert action==row['action'],(game,arm,row['step'],action,row['action'])
                if semantic_decision(json.loads(response))!=semantic_decision(json.loads(row['response'])):
                    (a.root/'replay_difference.json').write_text(json.dumps(dict(actual=json.loads(response),recorded=json.loads(row['response'])),indent=2))
                    raise AssertionError(('Decision changed',game,arm,row['step']))
                count+=1
            results.append(dict(game=game,arm=arm,matched_decisions=count,matched_all_prompt_hashes=True,
                final_code_cpu_and_assembly_seconds=sum(times),new_api_requests=0,
                qualification='Offline recorded-response replay; excludes network latency, not an independent game run'))
    (a.root/'compatibility.json').write_text(json.dumps(results,indent=2));print(json.dumps(results))


if __name__=='__main__':main()
