# Quiz System Implementation

## Quiz Models and Schemas

### Database Model (models/quiz.py)
```python
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base

class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    course_id = Column(Integer, ForeignKey("courses.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    questions = relationship("Question", back_populates="quiz")
    attempts = relationship("QuizAttempt", back_populates="quiz")

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"))
    question_text = Column(Text)
    question_type = Column(String)  # "multiple_choice", "true_false", "fill_blank"
    points = Column(Integer, default=1)
    order = Column(Integer)

    quiz = relationship("Quiz", back_populates="questions")
    options = relationship("QuestionOption", back_populates="question")
    answers = relationship("Answer", back_populates="question")

class QuestionOption(Base):
    __tablename__ = "question_options"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"))
    option_text = Column(Text)
    is_correct = Column(Boolean, default=False)

    question = relationship("Question", back_populates="options")

class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    score = Column(Integer)
    total_points = Column(Integer)
    completed_at = Column(DateTime(timezone=True), server_default=func.now())

    quiz = relationship("Quiz", back_populates="attempts")
    user = relationship("User")
    answers = relationship("Answer", back_populates="attempt")

class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("quiz_attempts.id"))
    question_id = Column(Integer, ForeignKey("questions.id"))
    selected_option_id = Column(Integer, ForeignKey("question_options.id"))
    answer_text = Column(Text)  # For fill-in-blank questions
    is_correct = Column(Boolean)
    points_awarded = Column(Integer)

    attempt = relationship("QuizAttempt", back_populates="answers")
    question = relationship("Question", back_populates="answers")
    selected_option = relationship("QuestionOption")
```

### Pydantic Schemas (schemas/quiz.py)
```python
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class QuestionOptionBase(BaseModel):
    option_text: str
    is_correct: bool

class QuestionOption(QuestionOptionBase):
    id: int

    class Config:
        from_attributes = True

class QuestionBase(BaseModel):
    question_text: str
    question_type: str
    points: int
    order: int

class Question(QuestionBase):
    id: int
    options: List[QuestionOption] = []

    class Config:
        from_attributes = True

class QuizBase(BaseModel):
    title: str
    description: str

class Quiz(QuizBase):
    id: int
    questions: List[Question] = []

    class Config:
        from_attributes = True

class QuizAttemptBase(BaseModel):
    quiz_id: int
    user_id: int

class QuizAttempt(QuizAttemptBase):
    id: int
    score: int
    total_points: int
    completed_at: datetime

    class Config:
        from_attributes = True

class SubmitAnswer(BaseModel):
    question_id: int
    selected_option_id: Optional[int] = None
    answer_text: Optional[str] = None

class SubmitQuiz(BaseModel):
    answers: List[SubmitAnswer]
```

## Quiz Router Implementation (routers/quizzes.py)
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas, database, utils
from ..utils.validators import validate_quiz_submission

router = APIRouter()

@router.post("/quizzes/", response_model=schemas.Quiz)
def create_quiz(quiz: schemas.QuizCreate, db: Session = Depends(database.get_db)):
    db_quiz = models.Quiz(**quiz.dict())
    db.add(db_quiz)
    db.commit()
    db.refresh(db_quiz)
    return db_quiz

@router.get("/quizzes/{quiz_id}", response_model=schemas.Quiz)
def get_quiz(quiz_id: int, db: Session = Depends(database.get_db)):
    quiz = db.query(models.Quiz).filter(models.Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return quiz

@router.post("/quizzes/{quiz_id}/submit", response_model=schemas.QuizAttempt)
def submit_quiz(
    quiz_id: int,
    submission: schemas.SubmitQuiz,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(utils.get_current_user)
):
    # Validate the quiz exists
    quiz = db.query(models.Quiz).filter(models.Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    # Validate the submission
    validation_errors = validate_quiz_submission(submission, quiz)
    if validation_errors:
        raise HTTPException(status_code=400, detail=validation_errors)

    # Calculate score
    score = 0
    total_points = 0

    for submitted_answer in submission.answers:
        question = db.query(models.Question).filter(
            models.Question.id == submitted_answer.question_id
        ).first()

        total_points += question.points

        # Find the correct answer based on question type
        if question.question_type == "multiple_choice":
            if submitted_answer.selected_option_id:
                option = db.query(models.QuestionOption).filter(
                    models.QuestionOption.id == submitted_answer.selected_option_id
                ).first()

                if option and option.is_correct:
                    score += question.points

        elif question.question_type == "fill_blank":
            # For fill-in-blank questions, check against predefined answers
            correct_answers = db.query(models.QuestionOption).filter(
                models.QuestionOption.question_id == question.id,
                models.QuestionOption.is_correct == True
            ).all()

            user_answer = submitted_answer.answer_text.lower().strip()
            for correct_answer in correct_answers:
                if user_answer == correct_answer.option_text.lower().strip():
                    score += question.points
                    break

    # Save the attempt
    attempt = models.QuizAttempt(
        quiz_id=quiz_id,
        user_id=current_user.id,
        score=score,
        total_points=total_points
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    # Save individual answers
    for submitted_answer in submission.answers:
        answer = models.Answer(
            attempt_id=attempt.id,
            question_id=submitted_answer.question_id,
            selected_option_id=submitted_answer.selected_option_id,
            answer_text=submitted_answer.answer_text,
            is_correct=False,  # Will be calculated based on the scoring above
            points_awarded=0
        )
        db.add(answer)

    db.commit()

    return attempt
```

## Quiz Validation Utilities (utils/validators.py)
```python
from typing import List, Dict
from .. import models, schemas

def validate_quiz_submission(
    submission: schemas.SubmitQuiz,
    quiz: models.Quiz
) -> List[str]:
    """
    Validates a quiz submission against the quiz structure
    Returns a list of validation errors
    """
    errors = []

    # Check that all required questions are answered
    quiz_questions = {q.id for q in quiz.questions}
    submitted_questions = {a.question_id for a in submission.answers}

    missing_questions = quiz_questions - submitted_questions
    if missing_questions:
        errors.append(f"Missing answers for questions: {missing_questions}")

    # Validate each answer
    for answer in submission.answers:
        # Find the corresponding question
        question = next((q for q in quiz.questions if q.id == answer.question_id), None)
        if not question:
            errors.append(f"Question {answer.question_id} does not exist in this quiz")
            continue

        # Validate answer based on question type
        if question.question_type == "multiple_choice":
            if not answer.selected_option_id:
                errors.append(f"No option selected for question {answer.question_id}")
            else:
                # Check if the selected option belongs to this question
                option_exists = any(
                    opt.id == answer.selected_option_id
                    for opt in question.options
                )
                if not option_exists:
                    errors.append(f"Invalid option selected for question {answer.question_id}")

        elif question.question_type == "fill_blank":
            if not answer.answer_text:
                errors.append(f"No answer provided for fill-in-blank question {answer.question_id}")

    return errors
```