import secrets
import string
from datetime import datetime, timedelta

def generate_assessment_token() -> str:
    """Generate a secure random token for assessment access"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(32))

def generate_candidate_access_link(assessment_candidate_id: int, token: str, base_url: str = "http://localhost:8000") -> str:
    """Generate access link for candidate"""
    return f"{base_url}/auth/candidate-login/{token}"

def calculate_assessment_score(assessment_candidate, db):
    """Calculate total score for an assessment candidate"""
    from app.models.submission import Submission
    
    submissions = db.query(Submission).filter(
        Submission.candidate_id == assessment_candidate.candidate_id,
        Submission.assessment_id == assessment_candidate.assessment_id,
        Submission.is_final_submission == True
    ).all()
    
    total_score = sum(sub.total_score for sub in submissions)
    questions_attempted = len(submissions)
    questions_correct = len([sub for sub in submissions if sub.total_score > 0])
    
    # Update assessment candidate record
    assessment_candidate.total_score = total_score
    assessment_candidate.questions_attempted = questions_attempted
    assessment_candidate.questions_correct = questions_correct
    
    # Calculate percentage based on max possible score
    max_possible_score = sum(
        aq.question.max_score * aq.weight 
        for aq in assessment_candidate.assessment.assessment_questions
    )
    
    if max_possible_score > 0:
        assessment_candidate.percentage_score = (total_score / max_possible_score) * 100
    else:
        assessment_candidate.percentage_score = 0
    
    db.commit()
    
    return assessment_candidate.total_score