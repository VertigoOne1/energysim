from pydantic import BaseModel as PydanticBaseModel, Field
from typing import *

class BaseModel(PydanticBaseModel):
    class Config:
        allow_population_by_field_name = True

from typing import *

class UserSignedUp(BaseModel):
  email: Optional[str] = Field(alias='Email of the user')
