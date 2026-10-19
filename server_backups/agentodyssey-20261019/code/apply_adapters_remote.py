import pathlib,difflib,json
R=pathlib.Path('/root/agentodyssey-benchmark-20261018');repo=R/'agentodyssey'
patches=[]
def edit(rel,old,new):
 p=repo/rel;before=p.read_text();assert old in before,(rel,old[:60]);after=before.replace(old,new,1);p.write_text(after)
 patches.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel))
(repo/'providers/deepseek_adapter.py').write_text((R/'deepseek_adapter.py').read_text())
edit('agents/llm_agent_config.py','        if llm_provider == "openai":','        if llm_name == "deepseek-flash":\n            from providers.deepseek_adapter import DeepSeekLanguageModel\n            return DeepSeekLanguageModel(llm_name=llm_name, max_new_tokens=self.max_new_tokens, temperature=self.temperature, top_p=self.top_p, presence_penalty=self.presence_penalty)\n\n        if llm_provider == "openai":')
edit('agents/rag/rag_agent_config.py','        if name.startswith("gpt"):', '        if name.startswith("gpt") or name.startswith("deepseek"):')
edit('agents/rag/rag_agent_config.py','                    "model": self.llm_name,','                    "model": self.llm_name,\n                    "openai_base_url": os.environ["AO_API_BASE_URL"],\n                    "api_key": "local-proxy",\n                    "max_tokens": 4096,\n                    "temperature": 0.1,')
edit('agents/rag/rag_agent_config.py','                    "model": self.embed_name,','                    "model": os.environ.get("AO_EMBED_PATH", self.embed_name),\n                    "model_kwargs": {"device": "cpu"},')
edit('agents/rag/rag_agent_config.py','            "vector_store": {','            "history_db_path": os.path.join(self.full_mem_path, "mem0_history.db"),\n            "vector_store": {')
edit('agents/rag/mem0_rag_agent.py','from providers.openai_api import OpenAILanguageModel','from providers.deepseek_adapter import DeepSeekLanguageModel as OpenAILanguageModel')
# Mem1 format repair only: preserve the 512-token approximate memory budget,
# state update algorithm, and action parser. This is a labelled adaptation,
# not the original trained MEM1 model or the unmodified upstream baseline.
edit('agents/fixed_size/fixed_size_memory_agent_config.py','    max_memory_tokens: int = 512 # for Constant Context Agent','''    max_memory_tokens: int = 512 # unchanged upstream approximate memory budget
    system_prompt: str = """
You are the player in a text adventure game. The world is described in text form.
At each turn, choose ONE action from the action space below.
Action space:
{}
Maintain a concise cumulative memory of essentials, approximately 512 tokens.
Output a single JSON object with exactly these keys:
{{"memory": "<IS>updated cumulative memory</IS>", "reasoning": "A few sentences explaining the action.", "action": "<action>"}}
The JSON must be the ONLY content in your reply. The action must match the action space.
"""''')
edit('agents/fixed_size/fixed_size_memory_agent_config.py','            "<IS>...</IS>\\n"\n            "Action: <action>\\n"','            \'A single JSON object with memory, reasoning, and action keys. \'\n            \'Put <IS>updated cumulative memory</IS> inside the memory string.\\n\'')
edit('agents/fixed_size/mem1_agent.py','        m = re.search(r"<IS>(.*?)</IS>", lm_output["response"], re.S | re.I)','        parsed_json = self.cfg.json_parser(lm_output["response"]) or {}\n        memory_text = parsed_json.get("memory", lm_output["response"])\n        m = re.search(r"<IS>(.*?)</IS>", memory_text if isinstance(memory_text, str) else "", re.S | re.I)')
(R/'compatibility.patch').write_text(''.join(patches))
print(json.dumps({'patched':True,'diff_lines':len(patches)}))
