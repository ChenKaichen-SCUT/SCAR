"""Lossless finite-Boolean grounding adapter for conformant POND inputs.

No observation translation is attempted. Explicit initial assignments avoid
incompatible 2005/2011 unknown/oneof dialects and mismatching domain declarations.
"""
def export(task):
    if task.resources or any(a.observation is not None for a in task.actions.values()):
        raise ValueError('adapter restricted to resource-free conformant tasks')
    def literal(i):return f'(f{i-1})' if i>0 else f'(not (f{-i-1}))'
    def form(x):
        if type(x) is bool:return '(and)' if x else '(or)'
        if type(x) is int:return literal(x)
        op,args=x
        if op=='oneof':raise ValueError('oneof action formula not supported by adapter')
        return '('+op+' '+' '.join(form(y) for y in args)+')'
    actions=[];mapping={}
    for i,a in enumerate(task.actions.values()):
        name=f'a{i}';mapping[name]=a.name
        effects=' '.join(literal(lit) if guard is True else f'(when {form(guard)} {literal(lit)})'
                         for guard,lit in a.effects)
        actions.append(f'(:action {name} :parameters () :precondition {form(a.pre)} :effect (and {effects}))')
    preds=' '.join(f'(f{i})' for i in range(len(task.atom_names)))
    d='(define (domain adapted) (:requirements :strips :negative-preconditions :conditional-effects :disjunctive-preconditions) (:predicates '+preds+') '+' '.join(actions)+')'
    states=[]
    for s in task.initial_bits:
        states.append('(and '+' '.join(literal(i+1 if s&(1<<i) else -i-1) for i in range(len(task.atom_names)))+')')
    # Formula init is explicitly supported by this author's PPDDL parser.
    p='(define (problem adapted) (:domain adapted) (:init (and (or '+' '.join(states)+'))) (:goal '+form(task.goal_expr)+'))'
    return d,p,mapping

def replay_sequence(task,mapping,sequence):
    worlds=[s for _,s in task.belief]
    for token in sequence:
        action=mapping[token]
        worlds=[task.step(s,action)[0] for s in worlds]
        if any(not task.allowed(s) for s in worlds):raise ValueError('illegal output action')
    if not all(task.goal.holds(s) for s in worlds):raise ValueError('output sequence does not reach all goals')
    return len(sequence)
