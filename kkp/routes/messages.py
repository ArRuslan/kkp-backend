from datetime import datetime, UTC

from fastapi import APIRouter
from tortoise.expressions import Q

from kkp.dependencies import JwtAuthUserDep
from kkp.models import Dialog, Message, User, Media
from kkp.schemas.common import PaginationResponse, PaginationQuery
from kkp.schemas.messages import DialogInfo, CreateMessageRequest, MessageInfo, MessagePaginationQuery
from kkp.utils.custom_exception import CustomMessageException

router = APIRouter(prefix="/messages")


@router.post("", response_model=PaginationResponse[DialogInfo])
async def list_dialogs(user: JwtAuthUserDep, query: PaginationQuery):
    dialogs_q = Dialog.filter(Q(to_user=user) | Q(from_user=user))

    return {
        "count": await dialogs_q.count(),
        "result": [
            await dialog.to_json(user)
            for dialog in await dialogs_q.all().select_related("from_user", "to_user") \
                .limit(query.page_size) \
                .offset(query.page_size * (query.page - 1))
        ],
    }


def make_dialog_q(this_user_id: int, other_user_id: int) -> Q:
    return Q(
        Q(dialog__to_user__id=this_user_id) & Q(dialog__from_user__id=other_user_id)
        | Q(dialog__to_user__id=other_user_id) & Q(dialog__from_user__id=this_user_id)
    )


@router.get("/{user_id}", response_model=PaginationResponse[MessageInfo])
async def get_messages(user_id: int, user: JwtAuthUserDep, query: MessagePaginationQuery):
    dialog_q = make_dialog_q(user.id, user_id)

    offset_q = Q()
    if query.before_date is not None:
        offset_q &= Q(date__lt=datetime.fromtimestamp(query.before_date, tz=UTC))
    if query.after_date is not None:
        offset_q &= Q(date__gt=datetime.fromtimestamp(query.after_date, tz=UTC))
    if query.before_id is not None:
        offset_q &= Q(id__lt=query.before_id)
    if query.after_id is not None:
        offset_q &= Q(id__gt=query.after_id)

    message_q = Message.filter(dialog_q & offset_q)

    limit = min(max(query.limit, 1), 100)
    related = ("dialog__from_user", "dialog__to_user", "author", "media")

    return {
        "count": await message_q.count(),
        "result": [
            await message.to_json(user)
            for message in await message_q.all().select_related(*related).limit(limit)
        ],
    }


@router.post("/{user_id}", response_model=MessageInfo)
async def send_message(user_id: int, user: JwtAuthUserDep, data: CreateMessageRequest):
    if (other_user := await User.get_or_none(id=user_id)) is None:
        raise CustomMessageException("Unknown dialog.", 404)

    dialog = await Dialog.get_or_none(make_dialog_q(user.id, other_user.id))
    if dialog is None:
        dialog = await Dialog.create(from_user=user, to_user=other_user)

    # TODO: send notification to other_user

    media = None
    if data.media_id is not None:
        if (media := await Media.get_or_none(id=data.media_id, uploaded_by=user)) is None:
            raise CustomMessageException("Media does not exist!")

    message = await Message.create(dialog=dialog, author=user, text=data.text, media=media)

    return await message.to_json(user)
