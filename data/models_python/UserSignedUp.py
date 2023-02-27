from pydantic import *
from typing import *

class UserSignedUp(BaseModel):
  email: Optional[str] = Field(alias='Email of the user')
