import os
os.environ.update(DATABASE_URL='sqlite:///:memory:',REDIS_URL='redis://localhost:6379/0',JWT_SECRET='test-secret',SEED_DEMO='false')
import sys
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','..','backend'))
import os,tempfile
_db=tempfile.NamedTemporaryFile(suffix='.db',delete=False);_db.close()
os.environ.update(DATABASE_URL='sqlite:///'+_db.name,REDIS_URL='redis://localhost:6379/0',JWT_SECRET='test-secret',SEED_DEMO='false')
import sys
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','..','backend'))
import src.database as dbmod
dbmod.engine.url=dbmod.engine.url
from sqlalchemy import create_engine
dbmod.engine=create_engine('sqlite:///'+_db.name)
from sqlalchemy.orm import sessionmaker
dbmod.Session.configure(bind=dbmod.engine)
from fastapi.testclient import TestClient
from sqlalchemy import select
from src.main import app
from src.database import Session,Base,engine
from src.models import *
from src.common import rows

Base.metadata.create_all(engine)
with Session() as s:
 from src.security import password_hash
 for role in ['operator','supervisor','viewer']:
  s.add(User(email=role+'@changqiao.local',password=password_hash('Address2026!'),role=role))
 s.add(Registry(id=1,now='2026-11-20T09:00:00'));s.commit()

c=TestClient(app)
def login(role):
 r=c.post('/auth/login',json={'email':role+'@changqiao.local','password':'Address2026!'})
 assert r.status_code==200,r.text
 return {'Authorization':'Bearer '+r.json()['token']}
sup=login('supervisor');op=login('operator');vw=login('viewer')
PASS=0;FAIL=0
def check(name,cond,extra=''):
 global PASS,FAIL
 if cond:PASS+=1;print('  PASS',name)
 else:FAIL+=1;print('  FAIL',name,extra)

with Session() as s:
 ids=[]
 for t in ['长桥路18号','长桥路十八号','长桥路81号','青石街2号']:
  e=Entrance(code=t,street=t[:3],number=18 if '18' in t or '十八' in t else (81 if '81' in t else 2),label=t,lat=31.2,lng=121.4);s.add(e);s.flush()
  a=Alias(entrance_id=e.id,text=t);s.add(a);s.flush();ids.append(a.id)
 s.commit()

def make_run(groups):
 with Session() as s:
  r=MatchRun(state='ready',result={'clusters':[{'alias_id':a,'label':l} for l,g in enumerate(groups) for a in g],'candidates':[],'evaluation':{},'source_sha256':'x','algorithm':'t'})
  s.add(r);s.flush();rid=r.id;s.commit()
 return rid

print('A) 角色权限：viewer/operator 不能发布簇批次')
rid=make_run([[ids[0],ids[1]],[ids[2]],[ids[3]]])
r=c.post('/batches',json={'run_id':rid},headers=vw);check('viewer 被拒 403',r.status_code==403,r.status_code)
r=c.post('/batches',json={'run_id':rid},headers=op);check('operator 被拒 403',r.status_code==403,r.status_code)

print('B) supervisor 发布首批并写入 register')
r=c.post('/batches',json={'run_id':rid},headers=sup);check('发布 200',r.status_code==200,r.text);b1=r.json()
reg=c.get('/register',headers=sup).json()
check('register 含新表',all(k in reg for k in ('batches','clusters','cluster_members','cluster_lineage')))
check('首批 3 个簇',len([x for x in reg['clusters'] if x['batch_id']==b1['id']])==3)
check('簇状态 active',b1['state']=='active')

print('C) 重算发布：续号与留痕')
rid2=make_run([[ids[0]],[ids[1]],[ids[2],ids[3]]])
r=c.post('/batches',json={'run_id':rid2},headers=sup);b2=r.json();check('二批发布成功',r.status_code==200,r.text)
reg=c.get('/register',headers=sup).json()
check('旧批归档、新批在用',[x['state'] for x in reg['batches']]==['archived','active'])
nos_b1={x['id']:x['cluster_no'] for x in reg['clusters'] if x['batch_id']==b1['id']}
nos_b2={x['id']:x['cluster_no'] for x in reg['clusters'] if x['batch_id']==b2['id']}
check('两批都有簇快照',len(nos_b1)==3 and len(nos_b2)==3)
rels={x['relation'] for x in reg['cluster_lineage'] if x['batch_id']==b2['id']}
check('lineage 完整记录拆/合去向',rels=={'split','merge','split_member','merge_member'},rels)

print('D) 发布重试幂等（同 run_id）')
r=c.post('/batches',json={'run_id':rid2},headers=sup)
check('重复发布返回同批次',r.status_code==200 and r.json()['id']==b2['id'])
n_clusters=len(reg['clusters']);n_lineage=len(reg['cluster_lineage'])
reg=c.get('/register',headers=sup).json()
check('簇/lineage 未重复',len(reg['clusters'])==n_clusters and len(reg['cluster_lineage'])==n_lineage)

print('E) 未就绪批次拒绝')
with Session() as s:
 q=MatchRun(state='queued');s.add(q);s.flush();qid=q.id;s.commit()
r=c.post('/batches',json={'run_id':qid},headers=sup);check('queued 返回 409',r.status_code==409,r.status_code)

print('F) 核验端点按簇号查询')
no=[x['cluster_no'] for x in reg['clusters'] if x['batch_id']==b2['id']][0]
r=c.get(f'/clusters/{no}',headers=sup);view=r.json()
check('返回多批成员',r.status_code==200 and len(view['batches'])>=1)
check('含 lineage 数组',isinstance(view['lineage'],list) and len(view['lineage'])>=1)
r=c.get('/clusters/99999',headers=sup);check('未知簇号 404/409',r.status_code in (404,409))

print('G) 鉴权：无 token 拒绝')
r=c.post('/batches',json={'run_id':rid});check('未登录 401',r.status_code==401)

print(f'\n{PASS} passed, {FAIL} failed')
sys.exit(1 if FAIL else 0)
