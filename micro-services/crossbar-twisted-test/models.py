import traceback
from pprint import pformat
from typing import Optional, List
from pydantic import BaseModel, ValidationError, PydanticValueError, validator, HttpUrl

class Phone(BaseModel):
   """Schema for Phone numbers"""
   mobile: str

class UserProfile(BaseModel):
   """Bla Bla"""
   username: str
   name: Optional[str]
   phone: Optional[Phone]
   mail: Optional[str]
   company: Optional[str]
   residence: Optional[str]
   website: Optional[List[HttpUrl]]
   job: Optional[str]
   address: Optional[str]

