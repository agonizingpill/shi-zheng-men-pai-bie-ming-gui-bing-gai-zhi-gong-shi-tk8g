import os,sys,types
os.environ.setdefault('DATABASE_URL','sqlite:///:memory:')
os.environ.setdefault('REDIS_URL','redis://localhost:6379/0')
os.environ.setdefault('JWT_SECRET','test-secret')
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','..','backend'))
from sqlalchemy import create_engine,select
from sqlalchemy.orm import sessionmaker
from src.database import Base
from src.models import *
from src import cluster_service as cs
from src.common import fail

engine=create_engine('sqlite:///:memory:')
Session=sessionmaker(engine,expire_on_commit=False)
def new_engine():
 global engine
 engine=create_engine('sqlite:///:memory:')
 Session.configure(bind=engine)
 Base.metadata.create_all(engine)
 with Session() as s:s.add(Registry(id=1,now='2026-11-20T09:00:00'));s.commit()
PASS=0;FAIL=0
def check(name,cond,extra=''):
 global PASS,FAIL
 if cond:PASS+=1;print('  PASS',name)
 else:FAIL+=1;print('  FAIL',name,extra)
def reset():new_engine()
def make_aliases(s,texts):
 ids=[]
 for t in texts:
  e=Entrance(code=t,street='长桥路',number=18,label=t,lat=31.2,lng=121.4);s.add(e);s.flush()
  a=Alias(entrance_id=e.id,text=t);s.add(a);s.flush();ids.append(a.id)
 return ids
def run_with(s,groups,state='ready'):
 r=MatchRun(state=state)
 if state=='ready':
  r.result={'clusters':[{'alias_id':a,'label':lab} for lab,g in enumerate(groups) for a in g]}
 s.add(r);s.flush();return r.id
def clusters_of(s,batch_id):
 out={}
 for c in s.scalars(select(Cluster).where(Cluster.batch_id==batch_id)).all():
  members=tuple(sorted(x.alias_id for x in s.scalars(select(ClusterMember).where(ClusterMember.cluster_id==c.id)).all()))
  out[members]=c.cluster_no
 return out
def lineage_edges(s,batch_id):
 rows=s.scalars(select(ClusterLineage).where(ClusterLineage.batch_id==batch_id)).all()
 return [(x.old_cluster_no,x.new_cluster_no,x.relation,x.shared) for x in rows]

print('1) 首批发布：新簇顺序编号，全部 new 去向')
reset()
with Session() as s:
 ids=make_aliases(s,['a','b','c','d'])
 rid=run_with(s,[[ids[0],ids[1]],[ids[2]],[ids[3]]])
 b=cs.publish_batch(s,rid);s.commit()
 got=clusters_of(s,b.id)
 check('三个簇编号 1/2/3',sorted(got.values())==[1,2,3],got)
 check('首批均为 new',all(x[2]=='new' for x in lineage_edges(s,b.id)))

print('2) 重算后整簇延续：旧号沿用，最大化续号别名数')
reset()
with Session() as s:
 ids=make_aliases(s,['a','b','c','d'])
 b1=cs.publish_batch(s,run_with(s,[[ids[0],ids[1]],[ids[2],ids[3]]]));s.commit()
 before=clusters_of(s,b1.id)
 b2=cs.publish_batch(s,run_with(s,[[ids[1],ids[0]],[ids[2],ids[3]]]));s.commit()
 after=clusters_of(s,b2.id)
 check('两簇旧号全部沿用',sorted(before.values())==sorted(after.values()))
 edges=lineage_edges(s,b2.id)
 check('两条 continued，共享别名数=簇大小',sorted(x[2] for x in edges)==['continued','continued'] and sorted(x[3] for x in edges)==[2,2],edges)
 check('旧批次归档',s.get(ClusterBatch,b1.id).state=='archived' and s.get(ClusterBatch,b2.id).state=='active')

print('3) 一个旧号只能续给一簇；最大化总续用别名（交换陷阱）')
reset()
with Session() as s:
 ids=make_aliases(s,['a','b','c'])
 b1=cs.publish_batch(s,run_with(s,[[ids[0],ids[1]],[ids[2]]]));s.commit()
 no=clusters_of(s,b1.id)
 old_big=no[(ids[0],ids[1])];old_small=no[(ids[2],)]
 b2=cs.publish_batch(s,run_with(s,[[ids[0]],[ids[1],ids[2]]]));s.commit()
 after=clusters_of(s,b2.id)
 total_kept=sum(len(set(k)&{a for a in ids}) for k,v in after.items() if v in (old_big,old_small))
 check('续号别名总数最大化（3个全部续用）',total_kept==3,after)
 check('每个旧号只续给一簇，无重复占用',len(set(after.values()))==len(after))
 check('新批次内簇号唯一',len(after.values())==len(set(after.values())))
 check('两批快照都保留同号簇',s.query(Cluster).count()==4)

print('4) 拆分：去向全部留痕，主续边 split + 附属 split_member')
reset()
with Session() as s:
 ids=make_aliases(s,['a','b','c'])
 b1=cs.publish_batch(s,run_with(s,[[ids[0],ids[1],ids[2]]]));s.commit()
 old_no=clusters_of(s,b1.id)[(ids[0],ids[1],ids[2])]
 b2=cs.publish_batch(s,run_with(s,[[ids[0]],[ids[1],ids[2]]]));s.commit()
 after=clusters_of(s,b2.id)
 check('主新簇沿用旧号',after[(ids[1],ids[2])]==old_no or after[(ids[0],)]==old_no)
 edges=lineage_edges(s,b2.id)
 rels=sorted(x[2] for x in edges)
 check('一条 split + 一条 split_member',rels==['split','split_member'],edges)
 check('边的共享别名数正确',sorted(x[3] for x in edges)==[1,2],edges)

print('5) 合到一起：merge + merge_member，新簇沿用贡献最大旧簇号')
reset()
with Session() as s:
 ids=make_aliases(s,['a','b','c'])
 b1=cs.publish_batch(s,run_with(s,[[ids[0]],[ids[1],ids[2]]]));s.commit()
 old_big=clusters_of(s,b1.id)[(ids[1],ids[2])]
 b2=cs.publish_batch(s,run_with(s,[[ids[0],ids[1],ids[2]]]));s.commit()
 after=clusters_of(s,b2.id)
 check('合并簇沿用大簇旧号',after[(ids[0],ids[1],ids[2])]==old_big,after)
 rels=sorted(x[2] for x in lineage_edges(s,b2.id))
 check('merge + merge_member 都留痕',rels==['merge','merge_member'],rels)

print('6) 消失与新增：retired / new')
reset()
with Session() as s:
 ids=make_aliases(s,['a','b','c','d'])
 b1=cs.publish_batch(s,run_with(s,[[ids[0]],[ids[1]]]));s.commit()
 b2=cs.publish_batch(s,run_with(s,[[ids[0]],[ids[2],ids[3]]]));s.commit()
 edges=lineage_edges(s,b2.id)
 check('旧簇 retired、新簇 new 且 continued 保留',('retired' in [x[2] for x in edges]) and ('new' in [x[2] for x in edges]) and ('continued' in [x[2] for x in edges]),edges)

print('7) 并发：接续基准是发布时在用批次，先发起晚算完不改在用号')
reset()
with Session() as s:
 ids=make_aliases(s,['a','b','c','d'])
 run_a=run_with(s,[[ids[0],ids[1]],[ids[2],ids[3]]],state='queued')
 run_b=run_with(s,[[ids[0]],[ids[1]],[ids[2],ids[3]]],state='queued')
 b1=cs.publish_batch(s,run_with(s,[[ids[0]],[ids[1]],[ids[2]],[ids[3]]]));s.commit()
 base_no=clusters_of(s,b1.id)
 run_b_ready=run_with(s,[[ids[0]],[ids[1]],[ids[2],ids[3]]])
 b_b=cs.publish_batch(s,run_b_ready);s.commit()
 run_a_ready=run_with(s,[[ids[0],ids[1]],[ids[2],ids[3]]])
 b_a=cs.publish_batch(s,run_a_ready);s.commit()
 check('只有一个在用批次',len([x for x in s.scalars(select(ClusterBatch)).all() if x.state=='active'])==1)
 check('最后发布者在用',s.get(ClusterBatch,b_a.id).state=='active')
 check('b_a 接续的是发布时在用的 b_b，而非最早基线',all(x.batch_id in (b_a.id,) for x in s.scalars(select(ClusterLineage).where(ClusterLineage.batch_id==b_a.id)).all()))
 edges_a=lineage_edges(s,b_a.id)
 check('b_a 与 b_b 的拆/合去向可追溯',set(x[2] for x in edges_a)>={'merge','merge_member'},edges_a)

print('8) 发布重试幂等：同 run 不重复占号')
reset()
with Session() as s:
 ids=make_aliases(s,['a','b'])
 rid=run_with(s,[[ids[0]],[ids[1]]])
 b1=cs.publish_batch(s,rid);b2=cs.publish_batch(s,rid);s.commit()
 check('两次发布返回同一批次',b1.id==b2.id)
 check('簇未重复创建',s.query(Cluster).count()==2)
 check('lineage 未重复写入',s.query(ClusterLineage).count()==2)

print('9) 未就绪批次拒绝发布')
reset()
with Session() as s:
 ids=make_aliases(s,['a','b'])
 rid=run_with(s,[[ids[0]],[ids[1]]],state='queued')
 try:cs.publish_batch(s,rid);check('queued 批次被拒',False)
 except Exception:check('queued 批次被拒',True)

print('10) 按簇号核验：跨批成员与去向')
reset()
with Session() as s:
 ids=make_aliases(s,['a','b','c'])
 b1=cs.publish_batch(s,run_with(s,[[ids[0],ids[1],ids[2]]]));s.commit()
 no=clusters_of(s,b1.id)[(ids[0],ids[1],ids[2])]
 b2=cs.publish_batch(s,run_with(s,[[ids[0]],[ids[1],ids[2]]]));s.commit()
 view=cs.cluster_lookup(s,no)
 check('能查到旧批与新批两个批次成员',len(view['batches'])==2,view['batches'])
 check('旧批成员仍可查',sorted(view['batches'],key=lambda x:x['batch_id'])[0]['members']==sorted(ids))
 check('去向含 split/split_member',{x['relation'] for x in view['lineage'] if x['direction']=='outgoing'}=={'split','split_member'},view['lineage'])
 try:cs.cluster_lookup(s,99999);check('未知簇号报错',False)
 except Exception:check('未知簇号报错',True)

print(f'\n{PASS} passed, {FAIL} failed')
sys.exit(1 if FAIL else 0)
