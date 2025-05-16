from datetime import datetime, UTC

from fastapi import APIRouter, Query
from tortoise.expressions import Q, Subquery
from tortoise.functions import Max

from kkp.dependencies import JwtAuthUserDep
from kkp.models import Dialog, Message, User, Media
from kkp.schemas.common import PaginationResponse, PaginationQuery
from kkp.schemas.messages import DialogInfo, CreateMessageRequest, MessageInfo, MessagePaginationQuery, \
    GetLastMessagesRequest, NewMessagesResponse, GetNewMessagesQuery
from kkp.utils.custom_exception import CustomMessageException

router = APIRouter(prefix="/messages")


# TODO: return dialogs ordered by last message time
# TODO: dont use pages, better use offsets, e.g. last message id offset
@router.get("", response_model=PaginationResponse[DialogInfo])
async def list_dialogs(user: JwtAuthUserDep, query: PaginationQuery = Query()):
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


# Note to myself: idk about that, maybe whole messages routes system needs rewrite.
#  Current implementation is good for just getting dialogs and messages.
#  But my biggest concern is processing new messages on clients, when they already have some messages,
#  for example if client does not have any messages, it just calls /messages (if on "dialogs" screen),
#  then /messages/last-messages, and if "dialog messages" screen is opened, it calls /messages/{user_id}
#  with specific offsets (e.g. before_id)
@router.post("/last-messages", response_model=dict[int, MessageInfo])
async def get_last_messages(user: JwtAuthUserDep, data: GetLastMessagesRequest):
    dialog_q = Q(dialog__to_user=user) | Q(dialog__from_user=user)

    messages = await Message.filter(id__in=Subquery(
        Message
        .filter(dialog_q & Q(dialog__id__in=data.dialog_ids))
        .group_by("dialog__id")
        .annotate(last_message_id=Max("id"))
        .values_list("last_message_id", flat=True)
    )).select_related("dialog__from_user", "dialog__to_user", "author", "media")

    return {
        message.dialog.id: await message.to_json(user)
        for message in messages
    }


"""
@router.get("/new-messages", response_model=NewMessagesResponse)
async def get_new_message(user: JwtAuthUserDep, query: GetNewMessagesQuery = Query()):
    dialog_q = Q(dialog__to_user=user) | Q(dialog__from_user=user)
    last_message_id = query.new_id
    if last_message_id == 0:
        last_message_id = await Message.filter(dialog_q).order_by("-id").values_list("id", flat=True).first()
    last_message_id = last_message_id or 0

    db_query = Message.filter(dialog_q & Q(id__gt=query.last_known_id, id__lte=last_message_id))
"""


def make_dialog_q(this_user_id: int, other_user_id: int, prefix: str = "") -> Q:
    to_user_q = f"{prefix}__to_user__id" if prefix else "to_user__id"
    from_user_q = f"{prefix}__from_user__id" if prefix else "from_user__id"
    return Q(
        Q(**{to_user_q: this_user_id}) & Q(**{from_user_q: other_user_id})
        | Q(**{to_user_q: other_user_id}) & Q(**{from_user_q: this_user_id})
    )


@router.get("/{user_id}", response_model=PaginationResponse[MessageInfo])
async def get_messages(user_id: int, user: JwtAuthUserDep, query: MessagePaginationQuery = Query()):
    dialog_q = make_dialog_q(user.id, user_id, "dialog")

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
