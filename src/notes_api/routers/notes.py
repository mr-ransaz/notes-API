from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, Response
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from notes_api.dependencies import CurrentUser, SessionDep
from notes_api.models import Note, User
from notes_api.schemas import NoteCreate, NotePatch, NoteQuery, NoteResponse

router = APIRouter(prefix="/notes", tags=["notes"])
NoteId = Annotated[int, Path(ge=1, le=2**63 - 1)]


def get_owned_note(note_id: int, user: User, session: Session) -> Note:
    note = session.scalar(
        select(Note).where(Note.id == note_id, Note.owner_id == user.id)
    )
    if note is None:
        raise HTTPException(404, "Note not found")
    return note


@router.post("", status_code=201, response_model=NoteResponse)
def create_note(data: NoteCreate, user: CurrentUser, session: SessionDep) -> Note:
    note = Note(owner_id=user.id, title=data.title, body=data.body)
    session.add(note)
    session.commit()
    return note


@router.get("", response_model=list[NoteResponse])
def list_notes(
    query: Annotated[NoteQuery, Query()], user: CurrentUser, session: SessionDep
) -> list[Note]:
    statement = select(Note).where(Note.owner_id == user.id)
    if query.q:
        statement = statement.where(
            or_(
                Note.title.icontains(query.q, autoescape=True),
                Note.body.icontains(query.q, autoescape=True),
            )
        )
    return list(
        session.scalars(
            statement.order_by(Note.id).limit(query.limit).offset(query.offset)
        )
    )


@router.get("/{note_id}", response_model=NoteResponse)
def read_note(note_id: NoteId, user: CurrentUser, session: SessionDep) -> Note:
    return get_owned_note(note_id, user, session)


@router.patch("/{note_id}", response_model=NoteResponse)
def update_note(
    note_id: NoteId, data: NotePatch, user: CurrentUser, session: SessionDep
) -> Note:
    note = get_owned_note(note_id, user, session)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(note, field, value)
    session.commit()
    return note


@router.delete("/{note_id}", status_code=204)
def delete_note(note_id: NoteId, user: CurrentUser, session: SessionDep) -> Response:
    note = get_owned_note(note_id, user, session)
    session.delete(note)
    session.commit()
    return Response(status_code=204)
