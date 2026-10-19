"""Read-only balance check against the already configured provider; never print keys."""
import json, urllib.request, urllib.error
from pathlib import Path
R=Path('/root/agentodyssey-benchmark-20261018')
key=(R/'.deepseek-key').read_text().strip()
req=urllib.request.Request('https://api.deepseek.com/user/balance',headers={'Authorization':'Bearer '+key})
try:
    with urllib.request.urlopen(req,timeout=30) as response:data=json.load(response)
    public={'is_available':data.get('is_available'),'balance_infos':data.get('balance_infos')}
except urllib.error.HTTPError as e:public={'status':e.code,'error':e.read().decode(errors='replace').replace(key,'[REDACTED]')[:500]}
(R/'deepseek_balance_check.json').write_text(json.dumps(public,indent=2))
print(json.dumps(public))
