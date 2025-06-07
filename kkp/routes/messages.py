from datetime import datetime, UTC

from fastapi import APIRouter, Query, BackgroundTasks
from tortoise.expressions import Q, Subquery
from tortoise.functions import Max

from kkp.dependencies import JwtAuthUserDep
from kkp.models import Dialog, Message, User, Media, MediaStatus
from kkp.schemas.common import PaginationResponse, PaginationQuery
from kkp.schemas.messages import DialogInfo, CreateMessageRequest, MessageInfo, MessagePaginationQuery, \
    GetLastMessagesRequest
from kkp.utils.cache import Cache
from kkp.utils.custom_exception import CustomMessageException
from kkp.utils.notification_util import send_notification

router = APIRouter(prefix="/messages")


# TODO: dont use pages? instead use offsets, e.g. last message id offset
@router.get("", response_model=PaginationResponse[DialogInfo])
async def list_dialogs(user: JwtAuthUserDep, query: PaginationQuery = Query()):
    dialogs_q = Dialog\
        .filter(Q(to_user=user) | Q(from_user=user))\
        .annotate(last_message=Max("messages__id"))\
        .order_by("-last_message")

    Cache.suffix(f"u{user.id}-withlast")
    return {
        "count": await dialogs_q.count(),
        "result": [
            await dialog.to_json(user, with_last_message=True)
            for dialog in await dialogs_q.all().select_related("from_user", "to_user") \
                .limit(query.page_size) \
                .offset(query.page_size * (query.page - 1))
        ],
    }


@router.post("/last-messages", response_model=dict[int, MessageInfo], deprecated=True)
async def get_last_messages(user: JwtAuthUserDep, data: GetLastMessagesRequest):  # pragma: no cover
    dialog_q = Q(dialog__to_user=user) | Q(dialog__from_user=user)

    Cache.suffix(f"u{user.id}")

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

    Cache.suffix(f"u{user.id}")

    return {
        "count": await Message.filter(dialog_q).count(),
        "result": [
            await message.to_json(user)
            for message in await message_q.all().select_related(*related).limit(limit).order_by("-id")
        ],
    }


async def _send_message_nofitication_task(to_user: User, from_user: User, text: str) -> None:
    await send_notification(
        to_user,
        "New message",
        (
                f"You have new message from {from_user.first_name}!\n"
                + (f"Comment: \n{text}" if text else "")
        ),
    )


@router.post("/{user_id}", response_model=MessageInfo)
async def send_message(user_id: int, user: JwtAuthUserDep, data: CreateMessageRequest, bg: BackgroundTasks):
    if (other_user := await User.get_or_none(id=user_id)) is None:
        raise CustomMessageException("Unknown dialog.", 404)

    dialog = await Dialog.get_or_none(make_dialog_q(user.id, other_user.id))
    if dialog is None:
        dialog = await Dialog.create(from_user=user, to_user=other_user)

    media = None
    if data.media_id is not None:
        if (media := await Media.get_or_none(id=data.media_id, uploaded_by=user, status=MediaStatus.UPLOADED)) is None:
            raise CustomMessageException("Media does not exist!")

    message = await Message.create(dialog=dialog, author=user, text=data.text, media=media)
    await Cache.delete_obj(dialog)

    if user != other_user:
        bg.add_task(_send_message_nofitication_task, other_user, user, message.text)

    Cache.suffix(f"u{user.id}")
    return await message.to_json(user)
