from pydantic import BaseModel,ConfigDict,Field
from typing import Literal
class Input(BaseModel):
 model_config=ConfigDict(extra='forbid',str_strip_whitespace=True,allow_inf_nan=False)
class Login(Input):
 email:str;password:str
class EntranceIn(Input):
 code:str=Field(min_length=2,max_length=40);street:str=Field(min_length=2,max_length=80);number:int=Field(ge=1,le=99999);label:str=Field(min_length=3,max_length=100);lat:float=Field(ge=-90,le=90);lng:float=Field(ge=-180,le=180)
class LocationIn(Input):
 lat:float=Field(ge=-90,le=90);lng:float=Field(ge=-180,le=180);reason:str=Field(min_length=8,max_length=400)
class AliasIn(Input):
 entrance_id:int;text:str=Field(min_length=3,max_length=120)
class EvidenceIn(Input):
 alias_id:int;reference:str=Field(min_length=3,max_length=100);description:str=Field(min_length=8,max_length=500)
class ProposalIn(Input):
 code:str=Field(min_length=2,max_length=40);source_id:int;target_id:int;reason:str=Field(min_length=8,max_length=500)
class ObjectionIn(Input):
 proposal_id:int;code:str=Field(min_length=2,max_length=40);note:str=Field(min_length=8,max_length=500)
class ResolveIn(Input):
 decision:Literal['uphold','split'];resolution:str=Field(min_length=8,max_length=500)
class NoticeIn(Input):
 proposal_id:int;days:int=Field(ge=3,le=30)
class ReasonIn(Input):
 reason:str=Field(min_length=8,max_length=500)
class ClockIn(Input):
 now:str;reason:str=Field(min_length=8,max_length=500)
