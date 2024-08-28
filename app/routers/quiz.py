from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlmodel import select

from app.classroom import find_room_by_code
from app.dependencies import get_db, templates
from app.model import Quiz

router = APIRouter(prefix="/quiz")


@router.get("/", response_class=HTMLResponse)
async def quiz_list(request: Request, db=Depends(get_db)):
    quizzes = db.exec(select(Quiz)).all()
    context = {"request": request, "quizzes": quizzes}
    return templates.TemplateResponse("quiz/main.html", context)


@router.post("/", response_class=HTMLResponse)
async def reject_name(request: Request, db=Depends(get_db)):
    for p in find_room_by_code("123-456").players.values():
        p.reject_name()
    return await quiz_list(request, db)
