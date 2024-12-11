import random
import uuid
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.exc import IntegrityError
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


async def get_question(question_id: uuid.UUID,
                       db: Annotated[Session, Depends(get_db)],
                       user: Annotated[User, Depends(current_user)]):
    question = db.exec(select(Question).where(Question.id == question_id)).one_or_none()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if question.quiz.owner != user and not question.quiz.is_public:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return question


async def get_answer(answer_id: uuid.UUID,
                     db: Annotated[Session, Depends(get_db)],
                     user: Annotated[User, Depends(current_user)]):
    answer = db.exec(select(Answer).where(Answer.id == answer_id)).one_or_none()
    if not answer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if answer.question.quiz.owner != user and not answer.question.quiz.is_public:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return answer


### Helpers ###
async def load_quiz_list(db: Annotated[Session, Depends(get_db)],
                         user: Annotated[User, Depends(current_user)]):
    return (db.exec(select(Quiz, Room)
                    .join(Room, isouter=True, onclause=and_(Room.quiz_id == Quiz.id, Room.owner == user))
                    .where(or_(Quiz.is_public == True, Quiz.owner == user)))
            .all())


### Routes ###

@router.get("/", response_class=HTMLResponse)
async def quiz_root(request: Request,
                    db: Annotated[Session, Depends(get_db)],
                    user: Annotated[User, Depends(current_user)]):
    """Show all quizzes that are public or owned by the user. Also show rooms owned by the user."""
    context = {"request": request, "user": user, "quizzes_and_rooms": await load_quiz_list(db, user)}
    return templates.TemplateResponse("quiz/main.html", context)


@router.get("/new_quiz_row_edit", response_class=HTMLResponse)
async def new_quiz_row_edit(request: Request):
    """Show the form for creating a new quiz."""
    context = {"request": request}
    return templates.TemplateResponse("partials/quiz/new_quiz_row_edit.html", context)


@router.post("/new_quiz_row", response_class=HTMLResponse)
async def new_quiz_row_post(request: Request,
                            quiz_name: Annotated[str, Form()],
                            db: Annotated[Session, Depends(get_db)],
                            user: Annotated[User, Depends(current_user)]):
    """Create a new quiz."""
    quiz = Quiz(name=quiz_name, owner=user)
    db.add(quiz)
    db.commit()
    context = {"request": request, "user": user, "quizzes_and_rooms": await load_quiz_list(db, user)}
    return templates.TemplateResponse("partials/quiz/quiz_list.html", context)


@router.get("/new_quiz_row", response_class=HTMLResponse)
async def new_quiz_row(request: Request):
    """Show the link for creating a new quiz, used when cancelling the creation of a new quiz."""
    context = {"request": request}
    return templates.TemplateResponse("partials/quiz/new_quiz_row.html", context)


@router.delete("/quiz_row/{quiz_id}", response_class=HTMLResponse)
async def quiz_row_delete(
        quiz: Annotated[Quiz, Depends(get_quiz)],
        db: Annotated[Session, Depends(get_db)],
        user: Annotated[User, Depends(current_user)]):
    """Delete an existing quiz."""
    if quiz.owner != user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    db.delete(quiz)
    db.commit()
    return ""


@router.get("/quiz_row_edit/{quiz_id}", response_class=HTMLResponse)
async def quiz_row_edit(request: Request,
                        quiz: Annotated[Quiz, Depends(get_quiz)],
                        user: Annotated[User, Depends(current_user)]):
    """Show a form to edit the name of a quiz."""
    if quiz.owner != user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    context = {"request": request, "quiz": quiz}
    return templates.TemplateResponse("partials/quiz/quiz_row_edit.html", context)


@router.get("/quiz_row/{quiz_id}", response_class=HTMLResponse)
async def quiz_row_get(request: Request,
                       db: Annotated[Session, Depends(get_db)],
                       quiz: Annotated[Quiz, Depends(get_quiz)],
                       user: Annotated[User, Depends(current_user)]):
    """Show an existing quiz name, used when cancelling an edit."""
    if quiz.owner != user and not quiz.is_public:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    room = db.exec(select(Room).where(and_(Room.quiz_id == quiz.id, Room.owner == user))).one_or_none()
    context = {"request": request, "user": user, "quiz": quiz, "room": room}
    return templates.TemplateResponse("partials/quiz/quiz_row.html", context)


@router.patch("/quiz_row/{quiz_id}", response_class=HTMLResponse)
async def quiz_row_patch(request: Request,
                         quiz_name: Annotated[str, Form()],
                         quiz: Annotated[Quiz, Depends(get_quiz)],
                         db: Annotated[Session, Depends(get_db)],
                         user: Annotated[User, Depends(current_user)]):
    """Update an existing quiz name."""
    if quiz.owner != user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    quiz.name = quiz_name
    db.add(quiz)
    db.commit()
    room = db.exec(select(Room).where(and_(Room.quiz_id == quiz.id, Room.owner == user))).one_or_none()
    context = {"request": request, "user": user, "quiz": quiz, "room": room}
    return templates.TemplateResponse("partials/quiz/quiz_row.html", context)


@router.get("/question_row_edit/{question_id}", response_class=HTMLResponse)
async def question_row_edit(request: Request,
                            question: Annotated[Question, Depends(get_question)],
                            selected_question: Annotated[Question | None, Depends(get_selected_question_no_check)],
                            user: Annotated[User, Depends(current_user)]):
    """Show a form to edit an existing question."""
    if question.quiz.owner != user and not question.quiz.is_public:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    context = {"request": request, "question": question, "selected_question": selected_question}
    return templates.TemplateResponse("partials/quiz/question_row_edit.html", context)


@router.patch("/question_row/{question_id}", response_class=HTMLResponse)
async def question_row_patch(request: Request,
                             question_text: Annotated[str, Form()],
                             question: Annotated[Question, Depends(get_question)],
                             db: Annotated[Session, Depends(get_db)],
                             user: Annotated[User, Depends(current_user)],
                             selected_question: Annotated[Question | None, Depends(get_selected_question_no_check)]):
    """Update an existing answer."""
    if question.quiz.owner != user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    question.text = question_text
    db.add(question)
    db.commit()
    context = {"request": request,
               "quiz": question.quiz,
               "editable": question.quiz.owner == user,
               "selected_question": selected_question}
    return templates.TemplateResponse("partials/quiz/detail_content.html", context)


@router.get("/question_row/{question_id}", response_class=HTMLResponse)
async def question_row_get(request: Request,
                           question: Annotated[Question, Depends(get_question)],
                           user: Annotated[User, Depends(current_user)],
                           selected_question: Annotated[Question | None, Depends(get_selected_question_no_check)]):
    """Show an existing question, used when cancelling an edit."""
    if question.quiz.owner != user and not question.quiz.is_public:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    context = {"request": request,
               "quiz": question.quiz,
               "question": question,
               "editable": question.quiz.owner == user,
               "selected_question": selected_question
               }
    return templates.TemplateResponse("partials/quiz/question_row.html", context)


@router.delete("/question_row/{question_id}", response_class=HTMLResponse)
async def question_row_delete(
        request: Request,
        question: Annotated[Question, Depends(get_question)],
        db: Annotated[Session, Depends(get_db)],
        user: Annotated[User, Depends(current_user)],
        selected_question: Annotated[Question | None, Depends(get_selected_question_no_check)]):
    """Delete an existing question."""
    quiz = question.quiz
    if quiz.owner != user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    db.delete(question)
    db.commit()
    if selected_question and selected_question.id == question.id:
        selected_question = None
    context = {"request": request,
               "quiz": quiz,
               "editable": quiz.owner == user,
               "selected_question": selected_question}
    response = templates.TemplateResponse("partials/quiz/detail_content.html", context)
    if selected_question:
        response.set_cookie("selected_question_id", value=str(selected_question.id), expires=259200,
                            secure=True, httponly=True, samesite="lax")
    else:
        response.delete_cookie("selected_question_id")
    return response


@router.get("/new_question_row/{quiz_id}", response_class=HTMLResponse)
async def new_question_row(request: Request,
                           quiz: Annotated[Quiz, Depends(get_quiz)]):
    """Show the link for creating a new question, used when cancelling the creation of a new question."""
    context = {"request": request, "quiz": quiz}
    return templates.TemplateResponse("partials/quiz/new_question_row.html", context)


@router.post("/new_question_row/{quiz_id}", response_class=HTMLResponse)
async def new_question_row_post(request: Request,
                                quiz: Annotated[Quiz, Depends(get_quiz)],
                                question_text: Annotated[str, Form()],
                                db: Annotated[Session, Depends(get_db)],
                                user: Annotated[User, Depends(current_user)]):
    """Create a new question."""
    if quiz.owner != user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    q = Question(text=question_text, quiz_id=quiz.id)
    db.add(q)
    db.commit()
    context = {"request": request,
               "quiz": quiz,
               "editable": quiz.owner == user,
               "selected_question": q}
    response = templates.TemplateResponse("partials/quiz/detail_content.html", context)
    response.set_cookie("selected_question_id", value=str(q.id), expires=259200,
                        secure=True, httponly=True, samesite="lax")
    return response


@router.get("/new_question_row_edit/{quiz_id}", response_class=HTMLResponse)
async def new_question_row_edit(request: Request,
                                quiz: Annotated[Quiz, Depends(get_quiz)],
                                user: Annotated[User, Depends(current_user)]):
    """Show the form for creating a new question."""
    if quiz.owner != user and not quiz.is_public:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    context = {"request": request, "quiz": quiz}
    return templates.TemplateResponse("partials/quiz/new_question_row_edit.html", context)


@router.get("/answer_row_edit/{answer_id}", response_class=HTMLResponse)
async def answer_row_edit(request: Request,
                          answer: Annotated[Answer, Depends(get_answer)],
                          user: Annotated[User, Depends(current_user)]):
    """Show a form to edit an existing answer."""
    if answer.question.quiz.owner != user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
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
    if answer.question.quiz.owner != user and not answer.question.quiz.is_public:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
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
    if selected_question.quiz.owner != user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
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
    if quiz.owner != user and not quiz.is_public:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    if not selected_question and quiz.questions:
        selected_question = quiz.questions[0]
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
    if quiz.owner != user and not quiz.is_public:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
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


@router.get("/{quiz_id}/create_room", response_class=HTMLResponse)
async def room_create(request: Request,
                      quiz: Annotated[Quiz, Depends(get_quiz)],
                      db: Annotated[Session, Depends(get_db)],
                      user: Annotated[User, Depends(current_user)]):
    if quiz.owner != user and not quiz.is_public:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    for i in range(50):
        code = ''.join(random.sample("34679CDFGHJKLMNPQRTVWX", 4))
        room = Room(code=code, quiz=quiz, owner=user)
        try:
            db.add(room)
            db.commit()
            return RedirectResponse(url=request.url_for('room_root', room_code=code),
                                    status_code=status.HTTP_303_SEE_OTHER)
        except IntegrityError:
            db.rollback()
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Unable to generate unique room code ")
