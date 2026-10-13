"""Historical token accounting plus measured official prompt growth, no test policy runs."""
import contextlib
import io
import json
import statistics
import tempfile
from pathlib import Path
from .common import RESULTS,ROOT,read_gzip,write
from .environment import create_initial
from .methods import make_method
from .preflight import MockProvider
from .provider import CONFIG
from scar.environment import AGENT_ID


def main():
    history=[]
    for path in (ROOT/'results/stage15').glob('requests_*.jsonl.gz'):
        for wrapper in read_gzip(path):
            row=wrapper.get('request',wrapper)
            if row.get('usage'):history.append(row)
    inputs=[r['usage']['prompt_tokens'] for r in history];outputs=[r['usage']['completion_tokens'] for r in history]
    measured={}
    with tempfile.TemporaryDirectory() as d:
        with contextlib.redirect_stdout(io.StringIO()):env,prefix=create_initial('quarantine',171906,Path(d)/'initial')
        obs=env.obs[AGENT_ID]
        for method in ('A0','A1','A2'):
            mock=MockProvider();agent=make_method(method,'quarantine',mock,'Craft and obtain 1 key.','key',prefix,Path(d)/method)
            for i in range(100):
                with contextlib.redirect_stdout(io.StringIO()):agent.act(dict(obs,step=obs['step']+i))
            lengths=[len((r['user']+(r['system'] or '')).encode()) for r in mock.calls]
            measured[method]=dict(first_utf8_bytes=lengths[0],last_utf8_bytes=lengths[-1],sum_utf8_bytes=24*sum(lengths),
                estimated_tokens_at_3_5_bytes=24*sum(lengths)/3.5,
                scope='old quarantine tutorial history and repeated old observation; no physical test trajectory; growth probe only')
    miss=CONFIG['pricing_usd_per_million']['cache_miss'];out=CONFIG['pricing_usd_per_million']['output']
    estimated={m:(v['estimated_tokens_at_3_5_bytes']*miss+2400*statistics.mean(outputs)*out)/1e6 for m,v in measured.items()}
    # Adaptive planner allowance: 3 full plan/revision calls per 10 actions plus
    # one in-plan question per 10 actions. An explicit sensitivity scenario,
    # not an observed holdout call count or a limit imposed on the method.
    ada_calls=24*10*4;ada_input=12000;ada_output=1200
    estimated['A3']=(ada_calls*ada_input*miss+ada_calls*ada_output*out)/1e6;estimated['A4']=0
    upper={m:(v['sum_utf8_bytes']*miss+2400*768*out)/1e6 for m,v in measured.items()}
    write(RESULTS/'budget_estimate.json',dict(max_environment_actions=12000,historical_stage15_requests=len(history),
        historical_input_mean=statistics.mean(inputs),historical_output_mean=statistics.mean(outputs),
        measured_prompt_growth=measured,no_cache_no_retry_scenario_usd=estimated,
        action_method_utf8_upper_scenario_usd=upper,adaplanner_scenario_calls=ada_calls,
        planned_hard_global_usd=CONFIG['total_budget_usd'],per_episode_guard_usd=CONFIG['episode_budget_usd'],
        true_worst_case='$200 global reservation cap, inclusive of uncertain request reserves. Per-run $12. All guards apply equally to every model method; aborts stay in denominator.',
        authorization='User explicitly waived the prior $20 cap for required experiments; no new cap permission requested.',
        limitations='Token/byte ratios, cache hits and planner revision frequency vary. These are planning scenarios, not guaranteed cost or billed invoice. No algorithm results used.'))

if __name__=='__main__':main()
