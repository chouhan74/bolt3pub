# from fastapi import APIRouter, Depends, Request, HTTPException, Cookie
# from fastapi.templating import Jinja2Templates
# from sqlalchemy.orm import Session
# from typing import Optional

# from app.core.database import get_db
# from app.models.assessment import AssessmentCandidate, AssessmentCandidateStatus
# from app.models.submission import Submission
# from app.models.proctoring import ProctoringEvent

# router = APIRouter()
# templates = Jinja2Templates(directory="app/templates")

# def get_current_candidate(
#     assessment_candidate_id: Optional[str] = Cookie(None),
#     candidate_session: Optional[str] = Cookie(None),
#     db: Session = Depends(get_db)
# ):
#     if not assessment_candidate_id or not candidate_session:
#         raise HTTPException(status_code=401, detail="Not authenticated")
    
#     try:
#         candidate_id = int(assessment_candidate_id)
#         assessment_candidate = db.query(AssessmentCandidate).filter(
#             AssessmentCandidate.id == candidate_id
#         ).first()
        
#         if not assessment_candidate:
#             raise HTTPException(status_code=404, detail="Assessment not found")
        
#         return assessment_candidate
#     except ValueError:
#         raise HTTPException(status_code=400, detail="Invalid candidate ID")

# @router.get("/assessment/{assessment_candidate_id}")
# async def assessment_interface(
#     request: Request,
#     assessment_candidate_id: int,
#     current_candidate: AssessmentCandidate = Depends(get_current_candidate),
#     db: Session = Depends(get_db)
# ):
#     if current_candidate.id != assessment_candidate_id:
#         raise HTTPException(status_code=403, detail="Access denied")
    
#     # Update status to in_progress if not already started
#     if current_candidate.status == AssessmentCandidateStatus.ASSIGNED:
#         current_candidate.status = AssessmentCandidateStatus.IN_PROGRESS
#         from datetime import datetime
#         current_candidate.started_at = datetime.utcnow()
#         db.commit()
    
#     # Get assessment questions
#     assessment = current_candidate.assessment
#     assessment_questions = assessment.assessment_questions
    
#     # Get candidate's submissions for this assessment
#     submissions = db.query(Submission).filter(
#         Submission.candidate_id == current_candidate.candidate_id,
#         Submission.assessment_id == assessment.id
#     ).all()
    
#     # Create a dict for quick lookup of submissions by question
#     submission_map = {sub.question_id: sub for sub in submissions if sub.is_final_submission}
    
#     return templates.TemplateResponse(
#         "candidate/assessment.html",
#         {
#             "request": request,
#             "assessment_candidate": current_candidate,
#             "assessment": assessment,
#             "assessment_questions": assessment_questions,
#             "submissions": submission_map,
#             "candidate": current_candidate.candidate
#         }
#     )

# @router.get("/question/{question_id}")
# async def question_interface(
#     request: Request,
#     question_id: int,
#     current_candidate: AssessmentCandidate = Depends(get_current_candidate),
#     db: Session = Depends(get_db)
# ):
#     # Verify question is part of current assessment
#     assessment_question = None
#     for aq in current_candidate.assessment.assessment_questions:
#         if aq.question_id == question_id:
#             assessment_question = aq
#             break
    
#     if not assessment_question:
#         raise HTTPException(status_code=404, detail="Question not found in assessment")
    
#     question = assessment_question.question
    
#     # Get public test cases only
#     public_test_cases = [tc for tc in question.test_cases if tc.is_public]
    
#     # Get candidate's latest submission for this question
#     latest_submission = db.query(Submission).filter(
#         Submission.candidate_id == current_candidate.candidate_id,
#         Submission.question_id == question_id,
#         Submission.assessment_id == current_candidate.assessment_id
#     ).order_by(Submission.submitted_at.desc()).first()
    
#     return templates.TemplateResponse(
#         "candidate/question.html",
#         {
#             "request": request,
#             "assessment_candidate": current_candidate,
#             "question": question,
#             "assessment_question": assessment_question,
#             "public_test_cases": public_test_cases,
#             "latest_submission": latest_submission,
#             "candidate": current_candidate.candidate
#         }
#     )

# @router.get("/results")
# async def candidate_results(
#     request: Request,
#     current_candidate: AssessmentCandidate = Depends(get_current_candidate),
#     db: Session = Depends(get_db)
# ):
#     if current_candidate.status not in [AssessmentCandidateStatus.SUBMITTED, AssessmentCandidateStatus.COMPLETED]:
#         raise HTTPException(status_code=400, detail="Assessment not yet completed")
    
#     # Get all submissions for this assessment
#     submissions = db.query(Submission).filter(
#         Submission.candidate_id == current_candidate.candidate_id,
#         Submission.assessment_id == current_candidate.assessment_id,
#         Submission.is_final_submission == True
#     ).all()
    
#     return templates.TemplateResponse(
#         "candidate/results.html",
#         {
#             "request": request,
#             "assessment_candidate": current_candidate,
#             "submissions": submissions,
#             "candidate": current_candidate.candidate
#         }
#     )
from fastapi import APIRouter, Depends, Request, HTTPException, Cookie, Path, Query
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.models.assessment import AssessmentCandidate, AssessmentCandidateStatus
from app.models.submission import Submission
from app.models.proctoring import ProctoringEvent

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def get_current_candidate_from_cookie(
    assessment_candidate_id: Optional[str] = Cookie(None),
    candidate_session: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Get candidate from cookie authentication"""
    if not assessment_candidate_id or not candidate_session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        candidate_id = int(assessment_candidate_id)
        assessment_candidate = db.query(AssessmentCandidate).filter(
            AssessmentCandidate.id == candidate_id
        ).first()
        
        if not assessment_candidate:
            raise HTTPException(status_code=404, detail="Assessment not found")
        
        return assessment_candidate
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid candidate ID")


def get_candidate_by_id(
    candidate_id: int,
    db: Session = Depends(get_db)
):
    """Get candidate by ID from database"""
    assessment_candidate = db.query(AssessmentCandidate).filter(
        AssessmentCandidate.id == candidate_id
    ).first()
    
    if not assessment_candidate:
        raise HTTPException(status_code=404, detail="Assessment not found")
    
    return assessment_candidate


async def render_assessment(request: Request, current_candidate: AssessmentCandidate, db: Session):
    """Common function to render assessment page"""
    # Update status to in_progress if not already started
    if current_candidate.status == AssessmentCandidateStatus.ASSIGNED:
        current_candidate.status = AssessmentCandidateStatus.IN_PROGRESS
        current_candidate.started_at = datetime.utcnow()
        db.commit()

    # Get assessment questions
    assessment = current_candidate.assessment
    assessment_questions = assessment.assessment_questions

    # Get candidate's submissions for this assessment
    submissions = db.query(Submission).filter(
        Submission.candidate_id == current_candidate.candidate_id,
        Submission.assessment_id == assessment.id,
    ).all()

    # Create a dict for quick lookup of submissions by question
    submission_map = {sub.question_id: sub for sub in submissions if sub.is_final_submission}

    return templates.TemplateResponse(
        "candidate/assessment.html",
        {
            "request": request,
            "assessment_candidate": current_candidate,
            "assessment": assessment,
            "assessment_questions": assessment_questions,
            "submissions": submission_map,
            "candidate": current_candidate.candidate,
        },
    )


# @router.get("/assessment/{assessment_candidate_id}")
# async def assessment_interface_with_path(
#     request: Request,
#     assessment_candidate_id: int = Path(..., description="Assessment candidate ID"),
#     db: Session = Depends(get_db)
# ):
#     """Assessment interface accessed via URL path parameter"""
#     # Get candidate by path parameter
#     current_candidate = get_candidate_by_id(assessment_candidate_id, db)
    
#     # Verify authentication via cookies
#     try:
#         cookie_candidate = get_current_candidate_from_cookie(db=db)
#         # Ensure path param matches authenticated candidate
#         if current_candidate.id != cookie_candidate.id:
#             raise HTTPException(status_code=403, detail="Access denied")
#     except HTTPException:
#         # If no valid cookie authentication, still allow access via path
#         # You might want to add additional security checks here
#         pass

#     return await render_assessment(request, current_candidate, db)


# @router.get("/assessment")
# async def assessment_interface_no_path(
#     request: Request,
#     current_candidate: AssessmentCandidate = Depends(get_current_candidate_from_cookie),
#     db: Session = Depends(get_db),
# ):
#     """Assessment interface accessed via cookie authentication only"""
#     return await render_assessment(request, current_candidate, db)
@router.get("/assessment/{assessment_candidate_id}")
async def assessment_interface_with_path(
    request: Request,
    assessment_candidate_id: int = Path(..., description="Assessment candidate ID"),
    db: Session = Depends(get_db),
    cookie_candidate: AssessmentCandidate = Depends(get_current_candidate_from_cookie),  # ✅ FIXED
):
    """Assessment interface accessed via URL path parameter"""
    # Get candidate by path parameter
    current_candidate = get_candidate_by_id(assessment_candidate_id, db)
    
    # Ensure path param matches authenticated candidate
    if cookie_candidate and current_candidate.id != cookie_candidate.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return await render_assessment(request, current_candidate, db)


@router.get("/assessment")
async def assessment_interface_no_path(
    request: Request,
    current_candidate: AssessmentCandidate = Depends(get_current_candidate_from_cookie),
    db: Session = Depends(get_db),
):
    """Assessment interface accessed via cookie authentication only"""
    return await render_assessment(request, current_candidate, db)

@router.get("/question/{question_id}")
async def question_interface(
    request: Request,
    question_id: int = Path(..., description="Question ID"),
    current_candidate: AssessmentCandidate = Depends(get_current_candidate_from_cookie),
    db: Session = Depends(get_db)
):
    """Question interface"""
    # Verify question is part of current assessment
    assessment_question = next(
        (aq for aq in current_candidate.assessment.assessment_questions if aq.question_id == question_id),
        None
    )
    if not assessment_question:
        raise HTTPException(status_code=404, detail="Question not found in assessment")

    question = assessment_question.question

    # Get public test cases only
    public_test_cases = [tc for tc in question.test_cases if tc.is_public]

    # Get candidate's latest submission for this question
    latest_submission = db.query(Submission).filter(
        Submission.candidate_id == current_candidate.candidate_id,
        Submission.question_id == question_id,
        Submission.assessment_id == current_candidate.assessment_id
    ).order_by(Submission.submitted_at.desc()).first()

    return templates.TemplateResponse(
        "candidate/question.html",
        {
            "request": request,
            "assessment_candidate": current_candidate,
            "question": question,
            "assessment_question": assessment_question,
            "public_test_cases": public_test_cases,
            "latest_submission": latest_submission,
            "candidate": current_candidate.candidate
        }
    )


@router.get("/results")
async def candidate_results(
    request: Request,
    current_candidate: AssessmentCandidate = Depends(get_current_candidate_from_cookie),
    db: Session = Depends(get_db)
):
    """Candidate results page"""
    if current_candidate.status not in [AssessmentCandidateStatus.SUBMITTED, AssessmentCandidateStatus.COMPLETED]:
        raise HTTPException(status_code=400, detail="Assessment not yet completed")

    # Get all final submissions for this assessment
    submissions = db.query(Submission).filter(
        Submission.candidate_id == current_candidate.candidate_id,
        Submission.assessment_id == current_candidate.assessment_id,
        Submission.is_final_submission == True
    ).all()

    return templates.TemplateResponse(
        "candidate/results.html",
        {
            "request": request,
            "assessment_candidate": current_candidate,
            "submissions": submissions,
            "candidate": current_candidate.candidate
        }
    )
