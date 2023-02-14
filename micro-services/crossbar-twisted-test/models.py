import traceback
from pprint import pformat
from typing import Optional, List
from pydantic import BaseModel, ValidationError, PydanticValueError, validator, HttpUrl

class Phone(BaseModel):
   """Schema for Phone numbers"""
   home: str
   mobile: str

class UserProfile(BaseModel):
   """Bla Bla"""
   username: str
   name: str
   phone: Phone
   mail: str
   company: Optional[str]
   residence: Optional[str]
   website: List[HttpUrl]
   job: Optional[str]
   address: Optional[str]

