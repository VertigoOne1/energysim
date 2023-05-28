from pydantic import BaseModel as PydanticBaseModel, Field
from typing import *

class BaseModel(PydanticBaseModel):
    class Config:
        allow_population_by_field_name = True

class UserSignUp(BaseModel):
  displayName: Optional[str] = Field(alias='Name of the user')
  email: Optional[str] = Field(alias='Email of the user')
  password: Optional[str] = Field(alias='Password for creation')
