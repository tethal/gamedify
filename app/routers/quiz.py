from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select

from app.dependencies import get_db, get_event_bus, templates
from app.model import Player, Quiz
from app.util import EventBus

router = APIRouter(prefix="/quiz")


@router.get("/", response_class=HTMLResponse)
async def quiz_list(request: Request, db=Depends(get_db)):
    quizzes = db.exec(select(Quiz)).all()
    context = {"request": request, "quizzes": quizzes}
    return templates.TemplateResponse("quiz/main.html", context)


@router.post("/", response_class=HTMLResponse)
async def reject_name(request: Request,
                      db: Annotated[Session, Depends(get_db)],
                      event_bus: Annotated[EventBus, Depends(get_event_bus)]):
    players = db.exec(select(Player)).all()
    for p in players:
        p.name = None
        db.add(p)
    db.commit()
    for p in players:
        event_bus.notify(p.id)
    return await quiz_list(request, db)
