from pydantic import BaseModel

from kkp.schemas.media import MediaInfo
from kkp.schemas.users import UserBaseInfo


class DialogInfo(BaseModel):
    id: int
    user: UserBaseInfo


class CreateMessageRequest(BaseModel):
    text: str
    media_id: int | None = None


class MessagePaginationQuery(BaseModel):
    before_date: int | None = None
    after_date: int | None = None
    before_id: int | None = None
    after_id: int | None = None
    limit: int = 100


class MessageInfo(BaseModel):
    id: int
    dialog: DialogInfo
    author: UserBaseInfo
    text: str
    media: MediaInfo | None
    date: int
