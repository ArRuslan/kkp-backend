from pydantic import BaseModel, Field

from kkp.schemas.media import MediaInfo
from kkp.schemas.users import UserBaseInfo


class MinMessageInfo(BaseModel):
    id: int
    text: str
    has_media: bool
    date: int


class DialogInfo(BaseModel):
    id: int
    user: UserBaseInfo
    last_message: MinMessageInfo | None


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


class GetLastMessagesRequest(BaseModel):
    dialog_ids: list[int] = Field(max_length=100)


class GetNewMessagesQuery(BaseModel):
    last_known_id: int
    chunk: int
    new_id: int = 0


class NewMessage(BaseModel):
    id: int
    dialog_id: int
    author_id: int
    text: str
    media: MediaInfo | None
    date: int


class NewMessagesResponse(BaseModel):
    total: int
    chunk: list[NewMessage]
    new_id: int
