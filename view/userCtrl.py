from flask_openapi3 import APIBlueprint
from pydantic import BaseModel, Field
from flask import request

from typing import Optional
from util.db import get_db_session
from schema.request_userCtrl import request_CreateUser, responst_CreateUser
from controller.Cont_userCtrl import createUser


class ErrorResponse(BaseModel):
    message: str
    detail: Optional[str] = None


userctrl = APIBlueprint("userctrl", __name__, url_prefix="/userCtrl")


@userctrl.post(
    "/createUser",
    summary="建新使用者",
    responses={200: responst_CreateUser},
)
def create_user(body: request_CreateUser):
    with get_db_session("default") as db:
        data = createUser(session=db, body=body)

        Outcome_dict = data.data()

        return Outcome_dict
