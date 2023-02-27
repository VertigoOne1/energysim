from pydantic import *
from typing import *

class UserSignUp(BaseModel):
  displayName: Optional[str] = Field(alias='Name of the user')
  email: Optional[str] = Field(alias='Email of the user')
  password: Optional[str] = Field(alias='Password for creation')
