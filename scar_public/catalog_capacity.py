"""Resource-independent sparse action catalogs over the same exact channels."""
from scar_public.resumable_capacity import ResumableCapacity


class CatalogCapacity(ResumableCapacity):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.catalogs={};self.catalog_builders={}
        self.work.update(catalog_lookups=0,catalog_hits=0,catalog_action_scans=0,depth_one_actions=0,
            resource_checks=0,resource_assemblies=0,child_assemblies=0)

    def catalog(self,projected):
        yield self.event('catalog_lookups')
        if projected in self.catalogs:
            self.work['catalog_hits']+=1
            return self.catalogs[projected]
        if projected not in self.catalog_builders:
            self.catalog_builders[projected]=self.build_catalog(projected)
        builder=self.catalog_builders[projected]
        while projected not in self.catalogs:
            try:yield next(builder)
            except StopIteration:break
        return self.catalogs[projected]

    def build_catalog(self,projected):
        rows=[]
        for index,a in enumerate(self.actions):
            yield self.event('catalog_action_scans')
            goals,channels=yield from self.template(projected,index)
            if goals or channels:rows.append((index,goals,channels))
        self.catalogs[projected]=tuple(rows)

    def compute(self,node):
        cap=node.mask.bit_count();best=0;resources,projected=node.key
        catalog=yield from self.catalog(projected)
        for index,(action_index,goals,channels) in enumerate(catalog):
            node.cursor=index;a=self.actions[action_index]
            yield self.event('action_visits')
            if resources:yield self.event('resource_checks',len(resources))
            if any(r<c for r,c in zip(resources,a.consumption)):
                node.closed=index+1;continue
            immediate=node.mask&goals;remaining=node.mask&~goals
            total=immediate.bit_count();prepared=[]
            node.edge_count=len(channels);node.edge_cursor=0
            if node.depth==1:
                # Every successor has zero remaining depth. Its contribution is
                # exactly zero; no child-key assembly or lookup is necessary.
                self.work['depth_one_actions']+=1
                if total>best:
                    best=total;node.lower=best;node.witness=(a.name,goals,())
                node.closed=index+1
                if best==cap:break
                continue
            if resources:yield self.event('resource_assemblies',len(resources))
            after_resources=tuple(r-c for r,c in zip(resources,a.consumption))
            ceiling=total
            for obs,projected_next,eligible in channels:
                yield self.event('edge_visits')
                mask=remaining&eligible
                if mask:
                    yield self.event('child_assemblies')
                    nxt=(after_resources,projected_next);child=self.node(nxt,mask,node.depth-1)
                    prepared.append((obs,nxt,mask,child));ceiling+=child.upper
            if min(cap,ceiling)<=best:
                self.work['dominated_actions']+=1;node.closed=index+1;continue
            if prepared:yield self.event('edge_visits',len(prepared))
            uncomputed=sum(child.upper for _,_,_,child in prepared)
            for j,(_,_,_,child) in enumerate(prepared):
                node.edge_cursor=j;yield self.event('edge_visits')
                uncomputed-=child.upper;node.waiting=child
                value=yield from self.evaluate(child)
                node.waiting=None;total+=value
                if min(cap,total+uncomputed)<=best:
                    self.work['dominated_actions']+=1;break
            else:
                value=min(cap,total)
                if value>best:
                    best=value;node.witness=(a.name,goals,tuple(prepared));node.lower=best
            node.closed=index+1;node.edge_cursor=node.edge_count
            if best==cap:break
        node.lower=node.upper=best;node.done=True;node.waiting=None
        self.work['completed_nodes']+=1;self.work['reductions']+=best<cap

    def frontier_cost(self,node):
        work=0;seen=set();current=node
        while current is not None and not current.done and id(current) not in seen:
            seen.add(id(current));catalog=self.catalogs.get(current.key[1])
            size=len(catalog) if catalog is not None else len(self.actions)
            work+=(3+2*len(current.key[0]))*max(0,size-current.closed)
            work+=3*max(0,current.edge_count-current.edge_cursor)
            current=current.waiting
        return max(1,work)
