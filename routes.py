from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session
from config import settings
from database import get_db
from gemini_service import GeminiService, GeminiServiceError
from models import User, WorkoutPlan
from schemas import FeedbackRequest, UserInput

router = APIRouter()
templates = Jinja2Templates(directory="templates")
ai = GeminiService()


def render_error(request: Request, message: str, status_code: int = 500):
    return templates.TemplateResponse(request=request, name="index.html", context={"error": message}, status_code=status_code)


def get_user_or_404(db: Session, user_id: str) -> User:
    user = db.scalar(select(User).where(User.user_id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def plan_to_dict(plan: WorkoutPlan):
    return {
        "id": plan.id,
        "original_plan": plan.original_plan,
        "updated_plan": plan.updated_plan,
        "nutrition_tip": plan.nutrition_tip,
        "feedback": plan.feedback,
        "created_at": plan.created_at,
        "updated_at": plan.updated_at,
    }


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={})


@router.post("/generate-workout", response_class=HTMLResponse)
def generate_workout_page(
    request: Request,
    name: str = Form(...),
    user_id: str = Form(...),
    age: int = Form(...),
    weight: float = Form(...),
    goal: str = Form(...),
    intensity: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        data = UserInput(name=name, user_id=user_id, age=age, weight=weight, goal=goal, intensity=intensity)
        workout = ai.generate_workout(data)
        nutrition = ai.generate_nutrition_tip(data)
        user = db.scalar(select(User).where(User.user_id == data.user_id))
        if user is None:
            user = User(**data.model_dump())
            db.add(user)
            db.flush()
        else:
            for key, value in data.model_dump().items():
                setattr(user, key, value)
        plan = user.plan
        if plan is None:
            plan = WorkoutPlan(user_pk=user.id, original_plan=workout.model_dump_json(indent=2), nutrition_tip=nutrition.model_dump_json(indent=2))
            db.add(plan)
        else:
            plan.original_plan = workout.model_dump_json(indent=2)
            plan.updated_plan = None
            plan.feedback = None
            plan.nutrition_tip = nutrition.model_dump_json(indent=2)
            plan.updated_at = None
        db.commit()
        db.refresh(user)
        db.refresh(plan)
        return templates.TemplateResponse(request=request, name="result.html", context={"user": user, "plan": plan, "message": "Your 7-day plan is ready."})
    except ValueError as exc:
        db.rollback()
        return render_error(request, str(exc), 400)
    except GeminiServiceError as exc:
        db.rollback()
        return render_error(request, str(exc), 503)
    except Exception as exc:
        db.rollback()
        return render_error(request, f"Could not generate the plan: {exc}", 500)


@router.post("/submit-feedback", response_class=HTMLResponse)
def submit_feedback_page(request: Request, user_id: str = Form(...), feedback: str = Form(...), db: Session = Depends(get_db)):
    try:
        req = FeedbackRequest(feedback=feedback)
        user = get_user_or_404(db, user_id)
        if user.plan is None:
            raise HTTPException(status_code=404, detail="No workout plan exists for this user")
        original = user.plan.updated_plan or user.plan.original_plan
        data = UserInput.model_validate({"name": user.name, "user_id": user.user_id, "age": user.age, "weight": user.weight, "goal": user.goal, "intensity": user.intensity})
        revised = ai.update_workout(data, original, req.feedback)
        user.plan.updated_plan = revised.model_dump_json(indent=2)
        user.plan.feedback = req.feedback
        user.plan.updated_at = datetime.now(timezone.utc)
        db.commit()
        return templates.TemplateResponse(request=request, name="result.html", context={"user": user, "plan": user.plan, "message": "Your plan was updated using your feedback."})
    except HTTPException:
        raise
    except GeminiServiceError as exc:
        db.rollback()
        return templates.TemplateResponse(request=request, name="result.html", context={"user": user if 'user' in locals() else None, "plan": user.plan if 'user' in locals() and user else None, "error": str(exc)}, status_code=503)


@router.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request, token: str | None = None, db: Session = Depends(get_db)):
    if token != settings.admin_token:
        return templates.TemplateResponse(request=request, name="admin_login.html", context={"error": None})
    users = db.scalars(select(User).order_by(User.created_at.desc())).all()
    return templates.TemplateResponse(request=request, name="all_users.html", context={"users": users})


@router.post("/admin", response_class=HTMLResponse)
def admin_login(request: Request, token: str = Form(...), db: Session = Depends(get_db)):
    if token != settings.admin_token:
        return templates.TemplateResponse(request=request, name="admin_login.html", context={"error": "Invalid admin token."}, status_code=401)
    return RedirectResponse(url=f"/admin?token={token}", status_code=303)


@router.post("/admin/delete")
def admin_delete_user(user_id: str = Form(...), token: str = Form(...), db: Session = Depends(get_db)):
    if token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Invalid admin token")
    user = db.scalar(select(User).where(User.user_id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return RedirectResponse(url=f"/admin?token={token}", status_code=303)


api_router = APIRouter(prefix="/api/v1", tags=["FitBuddy API"])


@api_router.get("/health")
def health():
    return {"status": "ok", "service": "fitbuddy"}


@api_router.post("/plans")
def api_generate_plan(payload: UserInput, db: Session = Depends(get_db)):
    try:
        workout = ai.generate_workout(payload)
        nutrition = ai.generate_nutrition_tip(payload)
        user = db.scalar(select(User).where(User.user_id == payload.user_id))
        if user is None:
            user = User(**payload.model_dump())
            db.add(user)
            db.flush()
        else:
            for key, value in payload.model_dump().items():
                setattr(user, key, value)
        if user.plan is None:
            plan = WorkoutPlan(user_pk=user.id, original_plan=workout.model_dump_json(indent=2), nutrition_tip=nutrition.model_dump_json(indent=2))
            db.add(plan)
        else:
            plan = user.plan
            plan.original_plan = workout.model_dump_json(indent=2)
            plan.updated_plan = None
            plan.feedback = None
            plan.nutrition_tip = nutrition.model_dump_json(indent=2)
            plan.updated_at = None
        db.commit()
        db.refresh(plan)
        return {"user": payload.model_dump(), "plan": plan_to_dict(plan)}
    except GeminiServiceError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@api_router.get("/plans/{user_id}")
def api_get_plan(user_id: str, db: Session = Depends(get_db)):
    user = get_user_or_404(db, user_id)
    if not user.plan:
        raise HTTPException(status_code=404, detail="No plan found")
    return {"user": {"name": user.name, "user_id": user.user_id, "age": user.age, "weight": user.weight, "goal": user.goal, "intensity": user.intensity}, "plan": plan_to_dict(user.plan)}


@api_router.post("/plans/{user_id}/feedback")
def api_feedback(user_id: str, payload: FeedbackRequest, db: Session = Depends(get_db)):
    try:
        user = get_user_or_404(db, user_id)
        if not user.plan:
            raise HTTPException(status_code=404, detail="No plan found")
        data = UserInput.model_validate({"name": user.name, "user_id": user.user_id, "age": user.age, "weight": user.weight, "goal": user.goal, "intensity": user.intensity})
        original = user.plan.updated_plan or user.plan.original_plan
        revised = ai.update_workout(data, original, payload.feedback)
        user.plan.updated_plan = revised.model_dump_json(indent=2)
        user.plan.feedback = payload.feedback
        user.plan.updated_at = datetime.now(timezone.utc)
        db.commit()
        return {"user": data.model_dump(), "plan": plan_to_dict(user.plan)}
    except GeminiServiceError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@api_router.get("/users")
def api_users(token: str, db: Session = Depends(get_db)):
    if token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Invalid admin token")
    users = db.scalars(select(User).order_by(User.created_at.desc())).all()
    return [{"user_id": u.user_id, "name": u.name, "age": u.age, "weight": u.weight, "goal": u.goal, "intensity": u.intensity, "plan": plan_to_dict(u.plan) if u.plan else None} for u in users]


@api_router.delete("/users/{user_id}")
def api_delete_user(user_id: str, token: str, db: Session = Depends(get_db)):
    if token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Invalid admin token")
    user = db.scalar(select(User).where(User.user_id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"message": "User deleted", "user_id": user_id}
