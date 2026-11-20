import numpy as np
from scipy.optimize import linear_sum_assignment
from .models import MatchRun,ClusterBatch,Cluster,ClusterMember,ClusterLineage
from .common import *

def _label_members(run):
 groups={}
 for x in run.result['clusters']:groups.setdefault(x['label'],set()).add(x['alias_id'])
 return groups

def _pair(old_groups,new_groups):
 old_labels=sorted(old_groups);new_labels=sorted(new_groups)
 w=np.zeros((len(old_labels),len(new_labels)),dtype=int)
 for i,o in enumerate(old_labels):
  for j,n in enumerate(new_labels):
   w[i,j]=len(old_groups[o]&new_groups[n])
 ri,ci=linear_sum_assignment(-w)
 pairs={}
 for i,j in zip(ri,ci):
  if w[i,j]>0:pairs[old_labels[i]]=new_labels[j]
 return pairs,w,old_labels,new_labels

def _add_members(s,cluster,alias_ids):
 for alias_id in sorted(alias_ids):s.add(ClusterMember(cluster_id=cluster.id,alias_id=alias_id))

def _lineage(s,batch_id,on,nn,relation,shared):
 s.add(ClusterLineage(batch_id=batch_id,old_cluster_no=on,new_cluster_no=nn,relation=relation,shared=shared))

def publish_batch(s,run_id):
 r=lock(s);run=get(s,MatchRun,run_id)
 existing=s.scalars(select(ClusterBatch).where(ClusterBatch.run_id==run_id)).first()
 if existing:return existing
 if run.state!='ready' or not run.result:fail('匹配批次尚未计算完成，不能发布簇号')
 prior=s.scalars(select(ClusterBatch).where(ClusterBatch.state=='active')).first()
 new_groups=_label_members(run)
 batch=ClusterBatch(run_id=run.id,state='active',published=r.now);s.add(batch);s.flush()
 if not prior:
  next_no=1
  for n in sorted(new_groups):
   c=Cluster(batch_id=batch.id,cluster_no=next_no);next_no+=1;s.add(c);s.flush()
   _add_members(s,c,new_groups[n])
   _lineage(s,batch.id,None,c.cluster_no,'new',0)
  s.flush();return batch
 old_groups=_label_members(get(s,MatchRun,prior.run_id))
 pairs,w,old_labels,new_labels=_pair(old_groups,new_groups)
 oi={o:i for i,o in enumerate(old_labels)};nj={n:j for j,n in enumerate(new_labels)}
 prior_clusters=[x for x in rows(s,Cluster) if x.batch_id==prior.id]
 member_ids_of={cluster.id:sorted(m.alias_id for m in rows(s,ClusterMember) if m.cluster_id==cluster.id) for cluster in prior_clusters}
 cluster_by_members={tuple(ids):cluster for cluster in prior_clusters for ids in [member_ids_of[cluster.id]]}
 old_cluster={label:cluster_by_members[tuple(sorted(old_groups[label]))] for label in old_labels}
 old_no={label:old_cluster[label].cluster_no for label in old_labels}
 incoming={n:[o for o in old_labels if w[oi[o],nj[n]]>0] for n in new_labels}
 outgoing={o:[n for n in new_labels if w[oi[o],nj[n]]>0] for o in old_labels}
 high=max(x.cluster_no for x in rows(s,Cluster))
 temp=high+1
 created={};temp_no={}
 for n in new_labels:
  c=Cluster(batch_id=batch.id,cluster_no=temp);s.add(c);s.flush();temp+=1
  _add_members(s,c,new_groups[n]);created[n]=c;temp_no[n]=c.cluster_no
 for o in old_labels:
  on=old_no[o]
  if not outgoing[o]:
   _lineage(s,batch.id,on,None,'retired',0);continue
  for n in outgoing[o]:
   if pairs.get(o)==n:
    split=len(outgoing[o])>1;merge=len(incoming[n])>1
    relation='continued' if not split and not merge else ('split_merge' if split and merge else ('split' if split else 'merge'))
   else:relation='split_member' if len(outgoing[o])>1 else 'merge_member'
   _lineage(s,batch.id,on,temp_no[n],relation,int(w[oi[o],nj[n]]))
 for n in new_labels:
  if not incoming[n]:_lineage(s,batch.id,None,temp_no[n],'new',0)
 final_no={}
 for n in new_labels:
  if n in pairs.values():
   old_label=next(o for o,m in pairs.items() if m==n);final_no[n]=old_no[old_label]
  else:high+=1;final_no[n]=high
 for n,c in created.items():c.cluster_no=final_no[n]
 temp_to_final={temp_no[n]:final_no[n] for n in new_labels}
 for x in rows(s,ClusterLineage):
  if x.batch_id==batch.id and x.new_cluster_no in temp_to_final:x.new_cluster_no=temp_to_final[x.new_cluster_no]
 prior.state='archived'
 s.flush();return batch

def cluster_lookup(s,no):
 matches=s.scalars(select(Cluster).where(Cluster.cluster_no==no).order_by(Cluster.batch_id)).all()
 if not matches:fail('簇号不存在')
 member_map={x.id:sorted(y.alias_id for y in rows(s,ClusterMember) if y.cluster_id==x.id) for x in rows(s,Cluster)}
 def batch_view(cluster):
  b=get(s,ClusterBatch,cluster.batch_id)
  return {'batch_id':b.id,'run_id':b.run_id,'state':b.state,'published':b.published,'cluster_no':cluster.cluster_no,'members':member_map[cluster.id]}
 out={'cluster_no':no,'batches':[batch_view(c) for c in matches],'lineage':[]}
 batch_ids={c.batch_id for c in matches}
 def peer_view(pno,batch_id):
  if batch_id in batch_ids:return
  pc=s.scalars(select(Cluster).where(Cluster.cluster_no==pno,Cluster.batch_id==batch_id)).first()
  if pc:out['batches'].append(batch_view(pc));batch_ids.add(batch_id)
 for x in rows(s,ClusterLineage):
  if x.old_cluster_no==no or x.new_cluster_no==no:
   side='outgoing' if x.old_cluster_no==no else 'incoming'
   pno=x.new_cluster_no if side=='outgoing' else x.old_cluster_no
   if pno:peer_view(pno,x.batch_id)
   out['lineage'].append({'batch_id':x.batch_id,'relation':x.relation,'direction':side,'shared':x.shared,'peer_cluster_no':pno})
 out['batches'].sort(key=lambda z:z['batch_id'])
 return out
