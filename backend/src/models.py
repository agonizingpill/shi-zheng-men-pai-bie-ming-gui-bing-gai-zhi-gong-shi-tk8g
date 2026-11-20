from sqlalchemy import Column,Integer,String,Float,ForeignKey,JSON,UniqueConstraint
from .database import Base
class User(Base):
 __tablename__='users'
 id=Column(Integer,primary_key=True);email=Column(String(160),unique=True,nullable=False);password=Column(String(160),nullable=False);role=Column(String(20),nullable=False)
class Registry(Base):
 __tablename__='registry'
 id=Column(Integer,primary_key=True);now=Column(String(32),nullable=False)
class Entrance(Base):
 __tablename__='entrances'
 id=Column(Integer,primary_key=True);code=Column(String(40),unique=True,nullable=False);street=Column(String(80),nullable=False);number=Column(Integer,nullable=False);label=Column(String(100),nullable=False);lat=Column(Float,nullable=False);lng=Column(Float,nullable=False)
class Alias(Base):
 __tablename__='aliases'
 id=Column(Integer,primary_key=True);entrance_id=Column(Integer,ForeignKey('entrances.id'),nullable=False);text=Column(String(120),unique=True,nullable=False);state=Column(String(20),default='verified',nullable=False)
class Evidence(Base):
 __tablename__='evidence'
 id=Column(Integer,primary_key=True);alias_id=Column(Integer,ForeignKey('aliases.id'),nullable=False);reference=Column(String(100),unique=True,nullable=False);description=Column(String(500),nullable=False)
class MatchRun(Base):
 __tablename__='match_runs'
 id=Column(Integer,primary_key=True);state=Column(String(20),default='queued');result=Column(JSON,nullable=True);error=Column(String(500),default='')
class Candidate(Base):
 __tablename__='candidates'
 id=Column(Integer,primary_key=True);run_id=Column(Integer,ForeignKey('match_runs.id'),nullable=False);source_id=Column(Integer,ForeignKey('entrances.id'),nullable=False);target_id=Column(Integer,ForeignKey('entrances.id'),nullable=False);similarity=Column(Float,nullable=False);conflict=Column(Integer,nullable=False)
class Proposal(Base):
 __tablename__='proposals'
 id=Column(Integer,primary_key=True);code=Column(String(40),unique=True,nullable=False);source_id=Column(Integer,ForeignKey('entrances.id'),nullable=False);target_id=Column(Integer,ForeignKey('entrances.id'),nullable=False);reason=Column(String(500),nullable=False);state=Column(String(20),default='draft',nullable=False)
class Objection(Base):
 __tablename__='objections'
 id=Column(Integer,primary_key=True);proposal_id=Column(Integer,ForeignKey('proposals.id'),nullable=False);code=Column(String(40),unique=True,nullable=False);note=Column(String(500),nullable=False);state=Column(String(20),default='open');decision=Column(String(30),default='');resolution=Column(String(500),default='')
class Notice(Base):
 __tablename__='notices'
 id=Column(Integer,primary_key=True);proposal_id=Column(Integer,ForeignKey('proposals.id'),unique=True,nullable=False);starts=Column(String(32),nullable=False);ends=Column(String(32),nullable=False);state=Column(String(20),default='public',nullable=False)
class Redirect(Base):
 __tablename__='redirects'
 id=Column(Integer,primary_key=True);source_id=Column(Integer,ForeignKey('entrances.id'),nullable=False);target_id=Column(Integer,ForeignKey('entrances.id'),nullable=False);proposal_id=Column(Integer,ForeignKey('proposals.id'),unique=True,nullable=False);state=Column(String(20),default='active');reason=Column(String(500),default='');created=Column(String(32),nullable=False)
class Audit(Base):
 __tablename__='audit'
 id=Column(Integer,primary_key=True);actor=Column(String(160),nullable=False);action=Column(String(100),nullable=False);detail=Column(String(500),nullable=False)
class ClusterBatch(Base):
 __tablename__='cluster_batches'
 id=Column(Integer,primary_key=True);run_id=Column(Integer,ForeignKey('match_runs.id'),unique=True,nullable=False);state=Column(String(20),default='active',nullable=False);published=Column(String(32),nullable=False)
class Cluster(Base):
 __tablename__='clusters'
 id=Column(Integer,primary_key=True);batch_id=Column(Integer,ForeignKey('cluster_batches.id'),nullable=False);cluster_no=Column(Integer,nullable=False)
 __table_args__=(UniqueConstraint('batch_id','cluster_no',name='uq_cluster_batch_no'),)
class ClusterMember(Base):
 __tablename__='cluster_members'
 id=Column(Integer,primary_key=True);cluster_id=Column(Integer,ForeignKey('clusters.id'),nullable=False);alias_id=Column(Integer,ForeignKey('aliases.id'),nullable=False)
 __table_args__=(UniqueConstraint('cluster_id','alias_id',name='uq_cluster_member'),)
class ClusterLineage(Base):
 __tablename__='cluster_lineage'
 id=Column(Integer,primary_key=True);batch_id=Column(Integer,ForeignKey('cluster_batches.id'),nullable=False);old_cluster_no=Column(Integer,nullable=True);new_cluster_no=Column(Integer,nullable=True);relation=Column(String(20),nullable=False);shared=Column(Integer,default=0,nullable=False)
 __table_args__=(UniqueConstraint('batch_id','old_cluster_no','new_cluster_no',name='uq_cluster_lineage_pair'),)
