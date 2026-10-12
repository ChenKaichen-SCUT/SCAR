"""Manually authored labels from public feedback, independent of parser output.

No hidden recipe catalogue or extractor is used to generate gold labels. This is
an in-repository annotation suite, NOT an independent human annotator or unseen
benchmark. The cited native observation is retained verbatim for review.
"""
from scar.io import atomic_json,digest
from scar_stage14.common import ROOT,episodes
from scar_v3.state import parse_action


def main():
    labels=[]
    def add(verb,target,form,recipes=None,quantities=None,stations=None):
        labels.append(dict(verb=verb,target=target,form=form,recipes=recipes or {},quantities=quantities or {},stations=stations or {}))
    add('inspect','bandage_roll','names',{'stitched_panel':['bandage_roll','sinew_cord'],'ruin_maul':['ruin_blade','wooden_rod','bandage_roll'],'war_strap':['sinew_cord','bandage_roll']})
    add('inspect','iron_nugget','names',{'iron_bar':['iron_nugget']})
    add('inspect','brimite_ingot','names',{'fiend_alloy':['brimite_ingot','hellcoal_concentrate'],'brimite_blade_blank':['brimite_ingot','wooden_rod']})
    add('inspect','fiend_alloy_sheet','names',{'fiend_shield':['fiend_alloy_sheet','timber_plate','war_strap','fiend_rivet'],'fiend_alloy_scale':['fiend_alloy_sheet']})
    add('inspect','hellcoal','names',{'hellcoal_concentrate':['hellcoal','devil_oil']})
    add('inspect','fiend_strip','names',{'fiend_rivet':['fiend_strip'],'war_codex':['field_journal','sinew_cord','fiend_strip']})
    add('inspect','brimite_nugget','names',{'brimite_ingot':['brimite_nugget']})
    add('inspect','brimite_ore','names',{'brimite_nugget':['brimite_ore']})
    add('inspect','gate_blank','names',{'siege_key':['gate_blank']})
    add('inspect','chain_net','names',{'machine_trap':['chain_net','cog_assembly','iron_bar']})
    add('inspect','forged_blade_blank','names',{'honed_blade':['forged_blade_blank','devil_oil']})
    add('inspect','brimite_blade_blank','names',{'brimite_blade':['brimite_blade_blank','demon_core_shard']})
    add('inspect','stitched_panel','names',{'war_pack':['stitched_panel','war_strap','iron_bar'],'padded_lining':['stitched_panel','salvage_cloth']})
    add('store','iron_nugget','quantified',{'iron_bar':['iron_nugget']},{'iron_bar':{'iron_nugget':2}})
    add('pick up','iron_nugget','quantified',{'iron_bar':['iron_nugget']},{'iron_bar':{'iron_nugget':2}})
    add('pick up','hellcoal','quantified',{'hellcoal_concentrate':['hellcoal','devil_oil']},{'hellcoal_concentrate':{'hellcoal':3,'devil_oil':1}})
    add('pick up','brimite_ingot','quantified',{'fiend_alloy':['brimite_ingot','hellcoal_concentrate'],'brimite_blade_blank':['brimite_ingot','wooden_rod']},{'fiend_alloy':{'brimite_ingot':1,'hellcoal_concentrate':1},'brimite_blade_blank':{'brimite_ingot':2,'wooden_rod':1}})
    add('pick up','stitched_panel','quantified',{'war_pack':['stitched_panel','war_strap','iron_bar'],'padded_lining':['stitched_panel','salvage_cloth']},{'war_pack':{'stitched_panel':2,'war_strap':2,'iron_bar':1},'padded_lining':{'stitched_panel':1,'salvage_cloth':1}})
    add('store','salvage_cloth','quantified',{
        'bandage_roll':['salvage_cloth','sinew_cord'],'oil_bomb':['oil_flask','charcoal_brick','salvage_cloth'],
        'scout_satchel':['salvage_cloth','sinew_cord'],'war_parchment':['salvage_cloth'],'sinew_cord':['salvage_cloth'],
        'war_banner':['salvage_cloth','wooden_rod'],'padded_lining':['stitched_panel','salvage_cloth'],
        'scrap_helm':['scrap_iron','salvage_cloth'],'ruin_gauntlets':['rubble_chunk','war_strap','salvage_cloth'],
        'scrap_lantern':['scrap_iron','devil_oil','salvage_cloth']},{
        'bandage_roll':{'salvage_cloth':1,'sinew_cord':2},'oil_bomb':{'oil_flask':1,'charcoal_brick':1,'salvage_cloth':1},
        'scout_satchel':{'salvage_cloth':3,'sinew_cord':1},'war_parchment':{'salvage_cloth':.25},'sinew_cord':{'salvage_cloth':.5},
        'war_banner':{'salvage_cloth':2,'wooden_rod':1},'padded_lining':{'stitched_panel':1,'salvage_cloth':1},
        'scrap_helm':{'scrap_iron':2,'salvage_cloth':1},'ruin_gauntlets':{'rubble_chunk':2,'war_strap':2,'salvage_cloth':1},
        'scrap_lantern':{'scrap_iron':1,'devil_oil':1,'salvage_cloth':1}})
    for target in ['sinew_cord','iron_nugget','brimite_ingot','fiend_alloy','fiend_strip']:
        add('craft',target,'station',stations={target:['war_bench' if target=='sinew_cord' else 'crucible']})
    for target in ['hunter_gauntlets','crucible','war_bench','padded_tunic','hellfire_bomb','fiend_helm','charcoal_stylus','inventory']:
        add('inspect',target,'negative')
    for target in ['sinew_cord','iron_nugget','fiend_strip']:add('craft',target,'success_no_recipe')
    found={}
    for stage,method,ep,case,path in episodes():
        for r in ep['rows']:
            p=parse_action(r['executed_action']);f=r['feedback']
            for i,label in enumerate(labels):
                if i in found or (p.verb,p.target)!=(label['verb'],label['target']):continue
                form=label['form']
                matches=('(made of ' in f if form=='names' else
                         'I have acquired a new item:' in f if form=='quantified' else
                         'Missing necessary' in f if form=='station' else
                         'successfully crafted' in f and 'It can be used to craft:' not in f if form=='success_no_recipe' else
                         'made of ' not in f and 'I have acquired a new item:' not in f)
                if matches:found[i]={'id':f'gold_{i:02d}','source_file':path,'source_task':ep['task_id'],
                    'source_index':r['index'],'stage':stage,'method':method,'action':r['executed_action'],
                    'observation':r['next_observation'],'raw_feedback':f,'expected':label,
                    'annotation_provenance':'manual public-feedback labels authored independently of extraction implementation'}
    assert len(found)==len(labels),(len(found),len(labels),[labels[i] for i in range(len(labels)) if i not in found])
    atomic_json(ROOT/'parser_gold.json',{'rows':[found[i] for i in range(len(labels))],
        'gold_not_generated_by_parser':True,'not_an_external_blind_annotator':True,'native_catalog_used':False})
    print({'annotated_native_feedbacks':len(found)})

if __name__=='__main__':main()
