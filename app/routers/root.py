from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlmodel import select

from app.dependencies import get_db, templates
from app.model import Quiz

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def root(request: Request, db=Depends(get_db)):
    quizzes = db.exec(select(Quiz)).all()
    context = {"request": request, "quizzes": quizzes}
    return templates.TemplateResponse("root.html", context)
