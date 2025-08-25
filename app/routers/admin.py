from fastapi import APIRouter, Depends, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List, Optional
import csv
import io
import json
import pandas as pd

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.user import User
from app.models.candidate import Candidate
from app.models.question import Question, TestCase, QuestionType, DifficultyLevel
from app.models.assessment import Assessment, AssessmentQuestion, AssessmentCandidate, AssessmentStatus
from app.models.submission import Submission
from app.models.proctoring import ProctoringEvent
from app.services.candidate_service import generate_assessment_token
from app.services.export_service import export_results_to_excel, export_results_to_csv

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/dashboard")
async def admin_dashboard(
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    # Get dashboard statistics
    total_candidates = db.query(Candidate).count()
    total_questions = db.query(Question).count()
    total_assessments = db.query(Assessment).count()
    active_assessments = db.query(Assessment).filter(
        Assessment.status == AssessmentStatus.ACTIVE
    ).count()
    
    # Recent submissions
    recent_submissions = db.query(Submission).order_by(
        Submission.submitted_at.desc()
    ).limit(10).all()
    
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "current_user": current_user,
            "total_candidates": total_candidates,
            "total_questions": total_questions,
            "total_assessments": total_assessments,
            "active_assessments": active_assessments,
            "recent_submissions": recent_submissions
        }
    )

# Candidates Management
@router.get("/candidates")
async def list_candidates(
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    candidates = db.query(Candidate).filter(Candidate.is_active == True).all()
    return templates.TemplateResponse(
        "admin/candidates.html",
        {"request": request, "current_user": current_user, "candidates": candidates}
    )

@router.get("/candidates/add")
async def add_candidate_form(
    request: Request,
    current_user: User = Depends(get_current_admin)
):
    return templates.TemplateResponse(
        "admin/candidate_form.html",
        {"request": request, "current_user": current_user, "candidate": None}
    )

@router.post("/candidates/add")
async def add_candidate(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(""),
    position: str = Form(""),
    experience_years: int = Form(0),
    skills: str = Form(""),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    # Check if candidate already exists
    existing = db.query(Candidate).filter(Candidate.email == email).first()
    if existing:
        return templates.TemplateResponse(
            "admin/candidate_form.html",
            {
                "request": request,
                "current_user": current_user,
                "candidate": None,
                "error": "Candidate with this email already exists"
            }
        )
    
    candidate = Candidate(
        name=name,
        email=email,
        phone=phone,
        position=position,
        experience_years=experience_years,
        skills=skills
    )
    
    db.add(candidate)
    db.commit()
    
    return RedirectResponse(url="/admin/candidates", status_code=302)

@router.get("/candidates/{candidate_id}/edit")
async def edit_candidate_form(
    request: Request,
    candidate_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    return templates.TemplateResponse(
        "admin/candidate_form.html",
        {"request": request, "current_user": current_user, "candidate": candidate}
    )

@router.post("/candidates/{candidate_id}/edit")
async def edit_candidate(
    request: Request,
    candidate_id: int,
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(""),
    position: str = Form(""),
    experience_years: int = Form(0),
    skills: str = Form(""),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    candidate.name = name
    candidate.email = email
    candidate.phone = phone
    candidate.position = position
    candidate.experience_years = experience_years
    candidate.skills = skills
    
    db.commit()
    
    return RedirectResponse(url="/admin/candidates", status_code=302)

@router.post("/candidates/import-csv")
async def import_candidates_csv(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith('.csv'):
        return templates.TemplateResponse(
            "admin/candidates.html",
            {
                "request": request,
                "current_user": current_user,
                "candidates": [],
                "error": "Please upload a CSV file"
            }
        )
    
    try:
        contents = await file.read()
        csv_file = io.StringIO(contents.decode('utf-8'))
        csv_reader = csv.DictReader(csv_file)
        
        added_count = 0
        for row in csv_reader:
            # Check if candidate exists
            existing = db.query(Candidate).filter(
                Candidate.email == row.get('email', '').strip()
            ).first()
            
            if not existing and row.get('email'):
                candidate = Candidate(
                    name=row.get('name', '').strip(),
                    email=row.get('email', '').strip(),
                    phone=row.get('phone', '').strip(),
                    position=row.get('position', '').strip(),
                    experience_years=int(row.get('experience_years', 0) or 0),
                    skills=row.get('skills', '').strip()
                )
                db.add(candidate)
                added_count += 1
        
        db.commit()
        
        candidates = db.query(Candidate).filter(Candidate.is_active == True).all()
        return templates.TemplateResponse(
            "admin/candidates.html",
            {
                "request": request,
                "current_user": current_user,
                "candidates": candidates,
                "success": f"Successfully imported {added_count} candidates"
            }
        )
    
    except Exception as e:
        candidates = db.query(Candidate).filter(Candidate.is_active == True).all()
        return templates.TemplateResponse(
            "admin/candidates.html",
            {
                "request": request,
                "current_user": current_user,
                "candidates": candidates,
                "error": f"Error importing CSV: {str(e)}"
            }
        )

# Questions Management
@router.get("/questions")
async def list_questions(
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    questions = db.query(Question).filter(Question.is_active == True).all()
    return templates.TemplateResponse(
        "admin/questions.html",
        {"request": request, "current_user": current_user, "questions": questions}
    )

@router.get("/questions/add")
async def add_question_form(
    request: Request,
    current_user: User = Depends(get_current_admin)
):
    return templates.TemplateResponse(
        "admin/question_form.html",
        {"request": request, "current_user": current_user, "question": None}
    )

@router.post("/questions/add")
async def add_question(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    question_type: str = Form(...),
    difficulty: str = Form(...),
    tags: str = Form(""),
    max_score: float = Form(100.0),
    time_limit_minutes: int = Form(30),
    template_code: str = Form(""),
    allowed_languages: str = Form("python,cpp,java"),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    question = Question(
        title=title,
        description=description,
        question_type=QuestionType(question_type),
        difficulty=DifficultyLevel(difficulty),
        tags=tags,
        max_score=max_score,
        time_limit_minutes=time_limit_minutes,
        template_code=template_code,
        allowed_languages=allowed_languages
    )
    
    db.add(question)
    db.commit()
    
    return RedirectResponse(url="/admin/questions", status_code=302)

@router.get("/questions/{question_id}/test-cases")
async def manage_test_cases(
    request: Request,
    question_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    test_cases = db.query(TestCase).filter(TestCase.question_id == question_id).all()
    
    return templates.TemplateResponse(
        "admin/test_cases.html",
        {
            "request": request,
            "current_user": current_user,
            "question": question,
            "test_cases": test_cases
        }
    )

@router.post("/questions/{question_id}/test-cases/add")
async def add_test_case(
    request: Request,
    question_id: int,
    input_data: str = Form(...),
    expected_output: str = Form(...),
    is_public: bool = Form(False),
    weight: float = Form(1.0),
    time_limit_seconds: int = Form(5),
    memory_limit_mb: int = Form(128),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    test_case = TestCase(
        question_id=question_id,
        input_data=input_data,
        expected_output=expected_output,
        is_public=is_public,
        weight=weight,
        time_limit_seconds=time_limit_seconds,
        memory_limit_mb=memory_limit_mb
    )
    
    db.add(test_case)
    db.commit()
    
    return RedirectResponse(url=f"/admin/questions/{question_id}/test-cases", status_code=302)

# Assessments Management
@router.get("/assessments")
async def list_assessments(
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    assessments = db.query(Assessment).all()
    return templates.TemplateResponse(
        "admin/assessments.html",
        {"request": request, "current_user": current_user, "assessments": assessments}
    )

@router.get("/assessments/add")
async def add_assessment_form(
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    questions = db.query(Question).filter(Question.is_active == True).all()
    return templates.TemplateResponse(
        "admin/assessment_form.html",
        {"request": request, "current_user": current_user, "assessment": None, "questions": questions}
    )

@router.post("/assessments/add")
async def add_assessment(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    instructions: str = Form(""),
    total_time_minutes: int = Form(120),
    max_score: float = Form(100.0),
    passing_score: float = Form(60.0),
    allow_copy_paste: bool = Form(False),
    allow_tab_switching: bool = Form(False),
    question_ids: List[str] = Form([]),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    assessment = Assessment(
        title=title,
        description=description,
        instructions=instructions,
        total_time_minutes=total_time_minutes,
        max_score=max_score,
        passing_score=passing_score,
        allow_copy_paste=allow_copy_paste,
        allow_tab_switching=allow_tab_switching
    )
    
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    
    # Add questions to assessment
    for i, question_id in enumerate(question_ids):
        if question_id:
            assessment_question = AssessmentQuestion(
                assessment_id=assessment.id,
                question_id=int(question_id),
                order_index=i,
                weight=1.0
            )
            db.add(assessment_question)
    
    db.commit()
    
    return RedirectResponse(url="/admin/assessments", status_code=302)

@router.get("/assessments/{assessment_id}/candidates")
async def manage_assessment_candidates(
    request: Request,
    assessment_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    
    candidates = db.query(Candidate).filter(Candidate.is_active == True).all()
    assigned_candidates = db.query(AssessmentCandidate).filter(
        AssessmentCandidate.assessment_id == assessment_id
    ).all()
    
    return templates.TemplateResponse(
        "admin/assessment_candidates.html",
        {
            "request": request,
            "current_user": current_user,
            "assessment": assessment,
            "candidates": candidates,
            "assigned_candidates": assigned_candidates
        }
    )

@router.post("/assessments/{assessment_id}/assign-candidate")
async def assign_candidate_to_assessment(
    request: Request,
    assessment_id: int,
    candidate_id: int = Form(...),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    # Check if already assigned
    existing = db.query(AssessmentCandidate).filter(
        AssessmentCandidate.assessment_id == assessment_id,
        AssessmentCandidate.candidate_id == candidate_id
    ).first()
    
    if not existing:
        assessment_candidate = AssessmentCandidate(
            assessment_id=assessment_id,
            candidate_id=candidate_id,
            access_token=generate_assessment_token()
        )
        db.add(assessment_candidate)
        db.commit()
    
    return RedirectResponse(url=f"/admin/assessments/{assessment_id}/candidates", status_code=302)

@router.get("/assessments/{assessment_id}/results")
async def assessment_results(
    request: Request,
    assessment_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    
    results = db.query(AssessmentCandidate).filter(
        AssessmentCandidate.assessment_id == assessment_id
    ).order_by(AssessmentCandidate.total_score.desc()).all()
    
    return templates.TemplateResponse(
        "admin/assessment_results.html",
        {
            "request": request,
            "current_user": current_user,
            "assessment": assessment,
            "results": results
        }
    )

@router.get("/assessments/{assessment_id}/results/export-csv")
async def export_assessment_results_csv(
    assessment_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    csv_content = export_results_to_csv(assessment_id, db)
    
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    filename = f"{assessment.title}_results.csv" if assessment else "results.csv"
    
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/assessments/{assessment_id}/results/export-excel")
async def export_assessment_results_excel(
    assessment_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    excel_content = export_results_to_excel(assessment_id, db)
    
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    filename = f"{assessment.title}_results.xlsx" if assessment else "results.xlsx"
    
    return Response(
        content=excel_content.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/proctoring/{assessment_id}")
async def proctoring_events(
    request: Request,
    assessment_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    
    events = db.query(ProctoringEvent).filter(
        ProctoringEvent.assessment_id == assessment_id
    ).order_by(ProctoringEvent.timestamp.desc()).all()
    
    return templates.TemplateResponse(
        "admin/proctoring_events.html",
        {
            "request": request,
            "current_user": current_user,
            "assessment": assessment,
            "events": events
        }
    )