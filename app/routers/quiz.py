from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session, and_, or_, select

from app.dependencies import current_user, get_db, templates
from app.model import Quiz, Room, User

router = APIRouter(prefix="/quiz")


@router.get("/", response_class=HTMLResponse)
async def quiz_root(request: Request,
                    db: Annotated[Session, Depends(get_db)],
                    user: Annotated[User, Depends(current_user)]):
    quizzes = (db.exec(select(Quiz, Room)
                       .join(Room, isouter=True, onclause=and_(Room.quiz_id == Quiz.id, Room.owner == user))
                       .where(or_(Quiz.is_public == True, Quiz.owner == user)))
               .all())
    context = {"request": request, "quizzes_and_rooms": quizzes}
    return templates.TemplateResponse("quiz/main.html", context)
