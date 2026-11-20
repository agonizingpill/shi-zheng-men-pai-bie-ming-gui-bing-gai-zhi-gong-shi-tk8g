from datetime import timedelta
from .models import Proposal,Notice,Objection,Alias,Evidence
from .common import *
from .proposal_service import pair
from .directory_service import activate
def publish(s,d):
 r=lock(s);p=get(s,Proposal,d['proposal_id'])
 if p.state!='draft':fail('只可公示草稿提案')
 pair(s,p.source_id,p.target_id)
 aliases={x.id for x in rows(s,Alias) if x.entrance_id==p.source_id}
 if not any(x.alias_id in aliases for x in rows(s,Evidence)):fail('来源入口缺少别名证据，不可公示')
 start=timestamp(r.now);n=Notice(proposal_id=p.id,starts=start.isoformat(),ends=(start+timedelta(days=d['days'])).isoformat());s.add(n);p.state='public';s.flush();return n
def effective(s,id):
 r=lock(s);n=get(s,Notice,id);p=get(s,Proposal,n.proposal_id)
 if n.state!='public' or p.state!='public':fail('公示不是待生效状态')
 if timestamp(r.now)<timestamp(n.ends):fail('公示期限未满')
 if any(x.proposal_id==p.id and x.state=='open' for x in rows(s,Objection)):fail('居民异议未结，不能生效')
 pair(s,p.source_id,p.target_id);redirect=activate(s,p,r.now);n.state='effective';p.state='active';return redirect
def advance(s,d):
 r=lock(s);new=timestamp(d['now'])
 if new<timestamp(r.now):fail('演示时钟不可倒退')
 r.now=new.isoformat();return r
