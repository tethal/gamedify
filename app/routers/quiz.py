import uuid
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from sqlmodel import Session, and_, or_, select

from app.dependencies import current_user, get_db, templates
from app.model import Answer, Question, Quiz, Room, User

router = APIRouter(prefix="/quiz")


### Dependencies ###

async def get_quiz(quiz_id: uuid.UUID,
                   db: Annotated[Session, Depends(get_db)],
                   user: Annotated[User, Depends(current_user)]):
    quiz = db.exec(select(Quiz).where(Quiz.id == quiz_id)).one_or_none()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if quiz.owner != user and not quiz.is_public:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return quiz


async def get_selected_question_no_check(db: Annotated[Session, Depends(get_db)],
                                         selected_question_id: Annotated[uuid.UUID | None, Cookie()] = None):
    if selected_question_id:
        return db.exec(select(Question).where(Question.id == selected_question_id)).one_or_none()


async def get_selected_question(quiz: Annotated[Quiz, Depends(get_quiz)],
                                selected_question: Annotated[Question | None, Depends(get_selected_question_no_check)]):
    if selected_question and selected_question.quiz_id == quiz.id:
        return selected_question


async def get_answer(answer_id: uuid.UUID,
                     db: Annotated[Session, Depends(get_db)],
                     user: Annotated[User, Depends(current_user)]):
    answer = db.exec(select(Answer).where(Answer.id == answer_id)).one_or_none()
    if not answer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if answer.question.quiz.owner != user and not answer.question.quiz.is_public:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return answer


### Routes ###

@router.get("/", response_class=HTMLResponse)
async def quiz_root(request: Request,
                    db: Annotated[Session, Depends(get_db)],
                    user: Annotated[User, Depends(current_user)]):
    """Show all quizzes that are public or owned by the user. Also show rooms owned by the user."""
    quizzes = (db.exec(select(Quiz, Room)
                       .join(Room, isouter=True, onclause=and_(Room.quiz_id == Quiz.id, Room.owner == user))
                       .where(or_(Quiz.is_public == True, Quiz.owner == user)))
               .all())
    context = {"request": request, "quizzes_and_rooms": quizzes}
    return templates.TemplateResponse("quiz/main.html", context)


@router.get("/answer_row_edit/{answer_id}", response_class=HTMLResponse)
async def answer_row_edit(request: Request,
                          answer: Annotated[Answer, Depends(get_answer)]):
    """Show a form to edit an existing answer."""
    context = {"request": request, "answer": answer}
    return templates.TemplateResponse("partials/quiz/answer_row_edit.html", context)


@router.patch("/answer_row/{answer_id}", response_class=HTMLResponse)
async def answer_row_patch(request: Request,
                           answer_text: Annotated[str, Form()],
                           answer: Annotated[Answer, Depends(get_answer)],
                           db: Annotated[Session, Depends(get_db)],
                           user: Annotated[User, Depends(current_user)]):
    """Update an existing answer."""
    if answer.question.quiz.owner != user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    answer.text = answer_text
    db.add(answer)
    db.commit()
    context = {"request": request, "answer": answer, "editable": answer.question.quiz.owner == user}
    return templates.TemplateResponse("partials/quiz/answer_row.html", context)


@router.get("/answer_row/{answer_id}", response_class=HTMLResponse)
async def answer_row_get(request: Request,
                         answer: Annotated[Answer, Depends(get_answer)],
                         user: Annotated[User, Depends(current_user)]):
    """Show an existing answer, used when cancelling an edit."""
    context = {"request": request, "answer": answer, "editable": answer.question.quiz.owner == user}
    return templates.TemplateResponse("partials/quiz/answer_row.html", context)


@router.delete("/answer_row/{answer_id}", response_class=HTMLResponse)
async def answer_row_delete(
        answer: Annotated[Answer, Depends(get_answer)],
        db: Annotated[Session, Depends(get_db)],
        user: Annotated[User, Depends(current_user)]):
    """Delete an existing answer."""
    if answer.question.quiz.owner != user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    db.delete(answer)
    db.commit()
    return ""


@router.get("/new_answer_row", response_class=HTMLResponse)
async def new_answer_row(request: Request):
    """Show the link for creating a new answer, used when cancelling the creation of a new answer."""
    context = {"request": request}
    return templates.TemplateResponse("partials/quiz/new_answer_row.html", context)


@router.post("/new_answer_row", response_class=HTMLResponse)
async def new_answer_row_post(request: Request,
                              answer_text: Annotated[str, Form()],
                              db: Annotated[Session, Depends(get_db)],
                              user: Annotated[User, Depends(current_user)],
                              selected_question: Annotated[Question | None, Depends(get_selected_question_no_check)]):
    """Create a new answer."""
    if not selected_question:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    a = Answer(text=answer_text, question_id=selected_question.id)
    db.add(a)
    db.commit()
    quiz = selected_question.quiz
    context = {"request": request,
               "quiz": quiz,
               "editable": quiz.owner == user,
               "selected_question": selected_question}
    return templates.TemplateResponse("partials/quiz/detail_content.html", context)


@router.get("/new_answer_row_edit", response_class=HTMLResponse)
async def new_answer_row_edit(request: Request):
    """Show the form for creating a new answer."""
    context = {"request": request}
    return templates.TemplateResponse("partials/quiz/new_answer_row_edit.html", context)


@router.get("/{quiz_id}", response_class=HTMLResponse)
async def quiz_detail(request: Request,
                      quiz: Annotated[Quiz, Depends(get_quiz)],
                      user: Annotated[User, Depends(current_user)],
                      selected_question: Annotated[Question | None, Depends(get_selected_question)]):
    """Show the details of a quiz, including all questions and answers."""
    context = {"request": request,
               "quiz": quiz,
               "editable": quiz.owner == user,
               "selected_question": selected_question}
    return templates.TemplateResponse("quiz/detail.html", context)


@router.post("/{quiz_id}/select/{question_id}", response_class=HTMLResponse)
async def quiz_select_question(request: Request,
                               quiz: Annotated[Quiz, Depends(get_quiz)],
                               question_id: uuid.UUID,
                               user: Annotated[User, Depends(current_user)]):
    """Select a question in the quiz, showing all its answers."""
    question = next((q for q in quiz.questions if q.id == question_id), None)
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    context = {"request": request,
               "quiz": quiz,
               "editable": quiz.owner == user,
               "selected_question": question}
    response = templates.TemplateResponse("partials/quiz/detail_content.html", context)
    response.set_cookie("selected_question_id", value=str(question.id), expires=259200,
                        secure=True, httponly=True, samesite="lax")
    return response
