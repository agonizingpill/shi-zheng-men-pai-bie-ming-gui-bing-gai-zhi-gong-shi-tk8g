from fastapi import HTTPException
from sqlalchemy import select
from .models import Registry,Audit
from datetime import datetime
def fail(msg):raise HTTPException(409,msg)
def get(s,cls,id):
 x=s.get(cls,id)
 if x is None:raise HTTPException(404,'记录不存在')
 return x
def lock(s):return s.scalars(select(Registry).where(Registry.id==1).with_for_update().execution_options(populate_existing=True)).one()
def log(s,u,action,detail):s.add(Audit(actor=u['email'],action=action,detail=str(detail)[:500]))
def rows(s,cls):return s.scalars(select(cls).order_by(cls.id)).all()
def dump(x):return {c.name:getattr(x,c.name) for c in x.__table__.columns}
def timestamp(v):
 try:return datetime.fromisoformat(v).replace(tzinfo=None)
 except ValueError:fail('时间必须为ISO格式')
