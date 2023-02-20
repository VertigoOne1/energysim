#!/bin/python3
from asyncapi_schema_pydantic import AsyncAPI

async_api = AsyncAPI.load_from_file("sample.yaml")
print(async_api.channels.get("user/signedup"))
print(async_api.components.messages.__len__())
print(async_api.components.messages.keys())
# sign_up_channel = async_api.channels.get("user/signedup")
# signed_up_msg = async_api.components.messages.get("UserSignedUp")
# print(signed_up_msg)
# print("")
# print(signed_up_msg.payload.properties)
async_api.components.messages.get("UserSignedUp").payload.properties["displayName"] = "Marnus"
async_api.components.messages.get("UserSignedUp").payload.properties["email"] = "marnus@gmail.com"
async_api.components.messages.get("UserSignedUp").payload.properties["bla"] = "bla"
print(async_api.json(by_alias=True, exclude_none=True, indent=2))
spec = AsyncAPI.load_from_file("sample.yaml")
AsyncAPI.validate(async_api)
print("")
# print(signed_up_msg)

# print(async_api.json(by_alias=True, exclude_none=True, indent=2))
