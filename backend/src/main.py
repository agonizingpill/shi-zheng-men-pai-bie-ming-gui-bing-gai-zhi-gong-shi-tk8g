from contextlib import asynccontextmanager
import os,logging,redis
from fastapi import FastAPI,HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select,text
from sqlalchemy.exc import IntegrityError
from .database import Session
from .models import User
from .security import password_hash,token_for
from .schemas import Login
from .middlewares import RequestTrace,Recovery
from .routes import router
logging.basicConfig(level=logging.INFO)
@asynccontextmanager
async def lifespan(app):
 from scripts.seed_demo import seed
 if os.getenv('SEED_DEMO','true')=='true':seed()
 yield
app=FastAPI(title='长桥门牌归并簿',lifespan=lifespan)
app.add_middleware(RequestTrace);app.add_middleware(Recovery);app.include_router(router)
@app.exception_handler(IntegrityError)
async def integrity(req,e):return JSONResponse({'detail':'编号或关联冲突，请核对已有记录'},409)
@app.get('/health')
def health():
 with Session() as s:s.execute(text('SELECT 1'))
 redis.from_url(os.environ['REDIS_URL']).ping();return {'status':'healthy'}
@app.post('/auth/login')
def login(d:Login):
 with Session() as s:
  u=s.scalars(select(User).where(User.email==d.email)).first()
  if not u or u.password!=password_hash(d.password):raise HTTPException(401,'账号或口令不正确')
  return {'token':token_for(u),'email':u.email,'role':u.role}
