from .models import Entrance,Alias,Evidence
from .common import *
def create_entrance(s,d):
 lock(s);x=Entrance(**d);s.add(x);s.flush();return x
def locate(s,id,d):
 lock(s);x=get(s,Entrance,id);x.lat=d['lat'];x.lng=d['lng'];return x
def alias(s,d):
 lock(s);get(s,Entrance,d['entrance_id']);x=Alias(**d);s.add(x);s.flush();return x
def evidence(s,d):
 lock(s);get(s,Alias,d['alias_id']);x=Evidence(**d);s.add(x);s.flush();return x
