# from fastapi import APIRouter, Depends, HTTPException, Request
# from sqlalchemy.orm import Session
# from typing import List, Dict, Any
# from pydantic import BaseModel
# import json
# import logging
# import redis
# from rq import Queue

# from app.core.database import get_db
# from app.core.config import settings
# from app.models.submission import Submission, SubmissionStatus
# from app.models.assessment import AssessmentCandidate
# from app.models.proctoring import ProctoringEvent, ProctoringEventType
# from app.routers.candidate import get_current_candidate
# from app.services.code_executor import execute_code_async

# router = APIRouter()
# logger = logging.getLogger(__name__)

# # Redis connection for job queue
# redis_conn = redis.Redis.from_url(settings.REDIS_URL)
# job_queue = Queue('code_execution', connection=redis_conn)

# class CodeExecutionRequest(BaseModel):
#     question_id: int
#     code: str
#     language: str
#     run_type: str = "test"  # "test" or "submit"

# class ProctoringEventRequest(BaseModel):
#     event_type: str
#     event_data: Dict[str, Any] = {}
#     severity: str = "medium"

# class AutoSaveRequest(BaseModel):
#     question_id: int
#     code: str

# @router.post("/execute-code")
# async def execute_code(
#     request_data: CodeExecutionRequest,
#     current_candidate: AssessmentCandidate = Depends(get_current_candidate),
#     db: Session = Depends(get_db)
# ):
#     try:
#         # Verify question is part of assessment
#         question_found = False
#         for aq in current_candidate.assessment.assessment_questions:
#             if aq.question_id == request_data.question_id:
#                 question_found = True
#                 break
        
#         if not question_found:
#             raise HTTPException(status_code=400, detail="Question not found in assessment")
        
#         # Create submission record
#         submission = Submission(
#             candidate_id=current_candidate.candidate_id,
#             question_id=request_data.question_id,
#             assessment_id=current_candidate.assessment_id,
#             code=request_data.code,
#             language=request_data.language,
#             is_final_submission=(request_data.run_type == "submit"),
#             status=SubmissionStatus.PENDING
#         )
        
#         db.add(submission)
#         db.commit()
#         db.refresh(submission)
        
#         # Queue the execution job
#         job = job_queue.enqueue(
#             execute_code_async,
#             submission.id,
#             request_data.run_type,
#             job_timeout=settings.CODE_EXECUTION_TIMEOUT + 10
#         )
        
#         return {
#             "submission_id": submission.id,
#             "job_id": job.id,
#             "status": "queued",
#             "message": "Code execution queued successfully"
#         }
        
#     except Exception as e:
#         logger.error(f"Error executing code: {str(e)}")
#         raise HTTPException(status_code=500, detail="Code execution failed")

# @router.get("/submission/{submission_id}/status")
# async def get_submission_status(
#     submission_id: int,
#     current_candidate: AssessmentCandidate = Depends(get_current_candidate),
#     db: Session = Depends(get_db)
# ):
#     submission = db.query(Submission).filter(
#         Submission.id == submission_id,
#         Submission.candidate_id == current_candidate.candidate_id
#     ).first()
    
#     if not submission:
#         raise HTTPException(status_code=404, detail="Submission not found")
    
#     return {
#         "submission_id": submission.id,
#         "status": submission.status.value,
#         "overall_verdict": submission.overall_verdict.value if submission.overall_verdict else None,
#         "total_score": submission.total_score,
#         "execution_time_ms": submission.execution_time_ms,
#         "memory_used_kb": submission.memory_used_kb,
#         "compilation_error": submission.compilation_error,
#         "runtime_error": submission.runtime_error,
#         "results": [
#             {
#                 "test_case_id": result.test_case_id,
#                 "verdict": result.verdict.value,
#                 "execution_time_ms": result.execution_time_ms,
#                 "memory_used_kb": result.memory_used_kb,
#                 "score": result.score,
#                 "actual_output": result.actual_output,
#                 "error_message": result.error_message
#             }
#             for result in submission.results
#         ] if submission.results else []
#     }

# @router.post("/proctoring-event")
# async def log_proctoring_event(
#     request: Request,
#     event_data: ProctoringEventRequest,
#     current_candidate: AssessmentCandidate = Depends(get_current_candidate),
#     db: Session = Depends(get_db)
# ):
#     try:
#         # Determine if this is a violation based on assessment settings
#         is_violation = False
#         assessment = current_candidate.assessment
        
#         if event_data.event_type == "copy_paste" and not assessment.allow_copy_paste:
#             is_violation = True
#         elif event_data.event_type == "tab_switch" and not assessment.allow_tab_switching:
#             is_violation = True
        
#         proctoring_event = ProctoringEvent(
#             candidate_id=current_candidate.candidate_id,
#             assessment_id=current_candidate.assessment_id,
#             event_type=ProctoringEventType(event_data.event_type),
#             event_data=json.dumps(event_data.event_data),
#             severity=event_data.severity,
#             is_violation=is_violation,
#             user_agent=request.headers.get("user-agent"),
#             ip_address=request.client.host if request.client else None
#         )
        
#         db.add(proctoring_event)
#         db.commit()
        
#         return {"status": "logged", "is_violation": is_violation}
        
#     except Exception as e:
#         logger.error(f"Error logging proctoring event: {str(e)}")
#         raise HTTPException(status_code=500, detail="Failed to log proctoring event")

# @router.post("/auto-save")
# async def auto_save_code(
#     save_data: AutoSaveRequest,
#     current_candidate: AssessmentCandidate = Depends(get_current_candidate),
#     db: Session = Depends(get_db)
# ):
#     try:
#         # For now, we'll store the auto-save as a non-final submission
#         # In a production system, you might want a separate auto-save table
        
#         # Check if there's a recent auto-save submission
#         from datetime import datetime, timedelta
#         recent_autosave = db.query(Submission).filter(
#             Submission.candidate_id == current_candidate.candidate_id,
#             Submission.question_id == save_data.question_id,
#             Submission.is_final_submission == False,
#             Submission.submitted_at > datetime.utcnow() - timedelta(minutes=1)
#         ).first()
        
#         if recent_autosave:
#             # Update existing auto-save
#             recent_autosave.code = save_data.code
#         else:
#             # Create new auto-save
#             autosave_submission = Submission(
#                 candidate_id=current_candidate.candidate_id,
#                 question_id=save_data.question_id,
#                 assessment_id=current_candidate.assessment_id,
#                 code=save_data.code,
#                 language="python",  # Default language for auto-save
#                 is_final_submission=False,
#                 status=SubmissionStatus.PENDING
#             )
#             db.add(autosave_submission)
        
#         db.commit()
        
#         return {"status": "saved"}
        
#     except Exception as e:
#         logger.error(f"Error auto-saving code: {str(e)}")
#         raise HTTPException(status_code=500, detail="Auto-save failed")

# @router.get("/assessment-time-remaining")
# async def get_time_remaining(
#     current_candidate: AssessmentCandidate = Depends(get_current_candidate)
# ):
#     if not current_candidate.started_at:
#         return {"time_remaining_minutes": current_candidate.assessment.total_time_minutes}
    
#     from datetime import datetime
#     elapsed = datetime.utcnow() - current_candidate.started_at
#     elapsed_minutes = elapsed.total_seconds() / 60
#     remaining_minutes = max(0, current_candidate.assessment.total_time_minutes - elapsed_minutes)
    
#     return {
#         "time_remaining_minutes": int(remaining_minutes),
#         "total_time_minutes": current_candidate.assessment.total_time_minutes,
#         "elapsed_minutes": int(elapsed_minutes)
#     }
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pydantic import BaseModel
import json
import logging
import redis
from rq import Queue

from app.core.database import get_db
from app.core.config import settings
from app.models.submission import Submission, SubmissionStatus
from app.models.assessment import AssessmentCandidate
from app.models.proctoring import ProctoringEvent, ProctoringEventType
from app.routers.candidate import get_current_candidate_from_cookie
from app.services.code_executor import execute_code_async

router = APIRouter()
logger = logging.getLogger(__name__)

# Redis connection for job queue
redis_conn = redis.Redis.from_url(settings.REDIS_URL)
job_queue = Queue('code_execution', connection=redis_conn)

class CodeExecutionRequest(BaseModel):
    question_id: int
    code: str
    language: str
    run_type: str = "test"  # "test" or "submit"

class ProctoringEventRequest(BaseModel):
    event_type: str
    event_data: Dict[str, Any] = {}
    severity: str = "medium"

class AutoSaveRequest(BaseModel):
    question_id: int
    code: str

@router.post("/execute-code")
async def execute_code(
    request_data: CodeExecutionRequest,
    current_candidate: AssessmentCandidate = Depends(get_current_candidate_from_cookie),
    db: Session = Depends(get_db)
):
    try:
        # Verify question is part of assessment
        question_found = False
        for aq in current_candidate.assessment.assessment_questions:
            if aq.question_id == request_data.question_id:
                question_found = True
                break
        
        if not question_found:
            raise HTTPException(status_code=400, detail="Question not found in assessment")
        
        # Create submission record
        submission = Submission(
            candidate_id=current_candidate.candidate_id,
            question_id=request_data.question_id,
            assessment_id=current_candidate.assessment_id,
            code=request_data.code,
            language=request_data.language,
            is_final_submission=(request_data.run_type == "submit"),
            status=SubmissionStatus.PENDING
        )
        
        db.add(submission)
        db.commit()
        db.refresh(submission)
        
        # Queue the execution job
        job = job_queue.enqueue(
            execute_code_async,
            submission.id,
            request_data.run_type,
            job_timeout=settings.CODE_EXECUTION_TIMEOUT + 10
        )
        
        return {
            "submission_id": submission.id,
            "job_id": job.id,
            "status": "queued",
            "message": "Code execution queued successfully"
        }
        
    except Exception as e:
        logger.error(f"Error executing code: {str(e)}")
        raise HTTPException(status_code=500, detail="Code execution failed")

@router.get("/submission/{submission_id}/status")
async def get_submission_status(
    submission_id: int,
    current_candidate: AssessmentCandidate = Depends(get_current_candidate_from_cookie),
    db: Session = Depends(get_db)
):
    submission = db.query(Submission).filter(
        Submission.id == submission_id,
        Submission.candidate_id == current_candidate.candidate_id
    ).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    return {
        "submission_id": submission.id,
        "status": submission.status.value,
        "overall_verdict": submission.overall_verdict.value if submission.overall_verdict else None,
        "total_score": submission.total_score,
        "execution_time_ms": submission.execution_time_ms,
        "memory_used_kb": submission.memory_used_kb,
        "compilation_error": submission.compilation_error,
        "runtime_error": submission.runtime_error,
        "results": [
            {
                "test_case_id": result.test_case_id,
                "verdict": result.verdict.value,
                "execution_time_ms": result.execution_time_ms,
                "memory_used_kb": result.memory_used_kb,
                "score": result.score,
                "actual_output": result.actual_output,
                "error_message": result.error_message
            }
            for result in submission.results
        ] if submission.results else []
    }

@router.post("/proctoring-event")
async def log_proctoring_event(
    request: Request,
    event_data: ProctoringEventRequest,
    current_candidate: AssessmentCandidate = Depends(get_current_candidate_from_cookie),
    db: Session = Depends(get_db)
):
    try:
        # Determine if this is a violation based on assessment settings
        is_violation = False
        assessment = current_candidate.assessment
        
        if event_data.event_type == "copy_paste" and not assessment.allow_copy_paste:
            is_violation = True
        elif event_data.event_type == "tab_switch" and not assessment.allow_tab_switching:
            is_violation = True
        
        proctoring_event = ProctoringEvent(
            candidate_id=current_candidate.candidate_id,
            assessment_id=current_candidate.assessment_id,
            event_type=ProctoringEventType(event_data.event_type),
            event_data=json.dumps(event_data.event_data),
            severity=event_data.severity,
            is_violation=is_violation,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None
        )
        
        db.add(proctoring_event)
        db.commit()
        
        return {"status": "logged", "is_violation": is_violation}
        
    except Exception as e:
        logger.error(f"Error logging proctoring event: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to log proctoring event")

@router.post("/auto-save")
async def auto_save_code(
    save_data: AutoSaveRequest,
    current_candidate: AssessmentCandidate = Depends(get_current_candidate_from_cookie),
    db: Session = Depends(get_db)
):
    try:
        # For now, we'll store the auto-save as a non-final submission
        # In a production system, you might want a separate auto-save table
        
        # Check if there's a recent auto-save submission
        from datetime import datetime, timedelta
        recent_autosave = db.query(Submission).filter(
            Submission.candidate_id == current_candidate.candidate_id,
            Submission.question_id == save_data.question_id,
            Submission.is_final_submission == False,
            Submission.submitted_at > datetime.utcnow() - timedelta(minutes=1)
        ).first()
        
        if recent_autosave:
            # Update existing auto-save
            recent_autosave.code = save_data.code
        else:
            # Create new auto-save
            autosave_submission = Submission(
                candidate_id=current_candidate.candidate_id,
                question_id=save_data.question_id,
                assessment_id=current_candidate.assessment_id,
                code=save_data.code,
                language="python",  # Default language for auto-save
                is_final_submission=False,
                status=SubmissionStatus.PENDING
            )
            db.add(autosave_submission)
        
        db.commit()
        
        return {"status": "saved"}
        
    except Exception as e:
        logger.error(f"Error auto-saving code: {str(e)}")
        raise HTTPException(status_code=500, detail="Auto-save failed")

@router.get("/assessment-time-remaining")
async def get_time_remaining(
    current_candidate: AssessmentCandidate = Depends(get_current_candidate_from_cookie)
):
    if not current_candidate.started_at:
        return {"time_remaining_minutes": current_candidate.assessment.total_time_minutes}
    
    from datetime import datetime
    elapsed = datetime.utcnow() - current_candidate.started_at
    elapsed_minutes = elapsed.total_seconds() / 60
    remaining_minutes = max(0, current_candidate.assessment.total_time_minutes - elapsed_minutes)
    
    return {
        "time_remaining_minutes": int(remaining_minutes),
        "total_time_minutes": current_candidate.assessment.total_time_minutes,
        "elapsed_minutes": int(elapsed_minutes)
    }