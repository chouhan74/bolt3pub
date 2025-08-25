from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import timedelta

from app.core.database import get_db
from app.core.security import verify_password, create_access_token, get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.candidate import Candidate
from app.models.assessment import AssessmentCandidate
from app.services.candidate_service import generate_assessment_token

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("auth/login.html", {"request": request})

@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()
    
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            "auth/login.html", 
            {"request": request, "error": "Invalid email or password"}
        )
    
    if not user.is_active:
        return templates.TemplateResponse(
            "auth/login.html", 
            {"request": request, "error": "Account is disabled"}
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    response = RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        expires=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    
    return response

@router.get("/candidate-login/{token}")
async def candidate_login_page(request: Request, token: str, db: Session = Depends(get_db)):
    # Verify assessment candidate token
    assessment_candidate = db.query(AssessmentCandidate).filter(
        AssessmentCandidate.access_token == token
    ).first()
    
    if not assessment_candidate:
        raise HTTPException(status_code=404, detail="Invalid access token")
    
    return templates.TemplateResponse(
        "auth/candidate_login.html",
        {
            "request": request,
            "token": token,
            "assessment": assessment_candidate.assessment,
            "candidate": assessment_candidate.candidate
        }
    )

@router.post("/candidate-login/{token}")
async def candidate_login(
    request: Request,
    token: str,
    name: str = Form(...),
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    # Verify assessment candidate token
    assessment_candidate = db.query(AssessmentCandidate).filter(
        AssessmentCandidate.access_token == token
    ).first()
    
    if not assessment_candidate:
        return templates.TemplateResponse(
            "auth/candidate_login.html",
            {"request": request, "token": token, "error": "Invalid access token"}
        )
    
    candidate = assessment_candidate.candidate
    
    # Basic validation - could be enhanced
    if candidate.email.lower() != email.lower() or candidate.name.lower() != name.lower():
        return templates.TemplateResponse(
            "auth/candidate_login.html",
            {
                "request": request,
                "token": token,
                "assessment": assessment_candidate.assessment,
                "candidate": candidate,
                "error": "Name or email doesn't match our records"
            }
        )
    
    # Create session token for candidate
    session_token = generate_assessment_token()
    
    response = RedirectResponse(
        url=f"/candidate/assessment/{assessment_candidate.id}",
        status_code=status.HTTP_302_FOUND
    )
    response.set_cookie(
        key="candidate_session",
        value=session_token,
        httponly=True,
        max_age=assessment_candidate.assessment.total_time_minutes * 60,
    )
    response.set_cookie(
        key="assessment_candidate_id",
        value=str(assessment_candidate.id),
        httponly=True,
        max_age=assessment_candidate.assessment.total_time_minutes * 60,
    )
    
    return response

@router.post("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("access_token")
    return response

@router.post("/candidate-logout")
async def candidate_logout():
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("candidate_session")
    response.delete_cookie("assessment_candidate_id")
    return response