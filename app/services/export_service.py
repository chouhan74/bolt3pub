import csv
import io
from typing import List
import pandas as pd
from sqlalchemy.orm import Session
from app.models.assessment import AssessmentCandidate, Assessment
from app.models.submission import Submission
from app.models.proctoring import ProctoringEvent

def export_results_to_csv(assessment_id: int, db: Session) -> str:
    """Export assessment results to CSV format"""
    
    # Get assessment and results
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        return ""
    
    results = db.query(AssessmentCandidate).filter(
        AssessmentCandidate.assessment_id == assessment_id
    ).all()
    
    # Create CSV content
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'Candidate Name',
        'Email',
        'Position',
        'Status',
        'Started At',
        'Submitted At',
        'Time Spent (minutes)',
        'Total Score',
        'Percentage Score',
        'Questions Attempted',
        'Questions Correct',
        'Passing Status'
    ])
    
    # Write data rows
    for result in results:
        candidate = result.candidate
        writer.writerow([
            candidate.name,
            candidate.email,
            candidate.position,
            result.status.value,
            result.started_at.isoformat() if result.started_at else '',
            result.submitted_at.isoformat() if result.submitted_at else '',
            result.total_time_spent_minutes,
            result.total_score,
            result.percentage_score,
            result.questions_attempted,
            result.questions_correct,
            'PASS' if result.percentage_score >= assessment.passing_score else 'FAIL'
        ])
    
    return output.getvalue()

def export_results_to_excel(assessment_id: int, db: Session) -> io.BytesIO:
    """Export assessment results to Excel format with multiple sheets"""
    
    # Get assessment and results
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        return io.BytesIO()
    
    results = db.query(AssessmentCandidate).filter(
        AssessmentCandidate.assessment_id == assessment_id
    ).all()
    
    # Create Excel writer
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')
    
    # Summary sheet
    summary_data = []
    for result in results:
        candidate = result.candidate
        summary_data.append({
            'Candidate Name': candidate.name,
            'Email': candidate.email,
            'Position': candidate.position,
            'Status': result.status.value,
            'Started At': result.started_at.isoformat() if result.started_at else '',
            'Submitted At': result.submitted_at.isoformat() if result.submitted_at else '',
            'Time Spent (minutes)': result.total_time_spent_minutes,
            'Total Score': result.total_score,
            'Percentage Score': result.percentage_score,
            'Questions Attempted': result.questions_attempted,
            'Questions Correct': result.questions_correct,
            'Passing Status': 'PASS' if result.percentage_score >= assessment.passing_score else 'FAIL'
        })
    
    df_summary = pd.DataFrame(summary_data)
    df_summary.to_excel(writer, sheet_name='Summary', index=False)
    
    # Detailed submissions sheet
    submissions_data = []
    for result in results:
        candidate = result.candidate
        submissions = db.query(Submission).filter(
            Submission.candidate_id == candidate.id,
            Submission.assessment_id == assessment_id,
            Submission.is_final_submission == True
        ).all()
        
        for submission in submissions:
            question_title = "Unknown"
            for aq in assessment.assessment_questions:
                if aq.question_id == submission.question_id:
                    question_title = aq.question.title
                    break
            
            submissions_data.append({
                'Candidate Name': candidate.name,
                'Email': candidate.email,
                'Question': question_title,
                'Language': submission.language,
                'Status': submission.status.value,
                'Verdict': submission.overall_verdict.value if submission.overall_verdict else '',
                'Score': submission.total_score,
                'Execution Time (ms)': submission.execution_time_ms,
                'Memory Used (KB)': submission.memory_used_kb,
                'Submitted At': submission.submitted_at.isoformat()
            })
    
    df_submissions = pd.DataFrame(submissions_data)
    df_submissions.to_excel(writer, sheet_name='Submissions', index=False)
    
    # Proctoring events sheet
    proctoring_data = []
    events = db.query(ProctoringEvent).filter(
        ProctoringEvent.assessment_id == assessment_id
    ).all()
    
    for event in events:
        proctoring_data.append({
            'Candidate Name': event.candidate.name,
            'Email': event.candidate.email,
            'Event Type': event.event_type.value,
            'Severity': event.severity,
            'Is Violation': event.is_violation,
            'Timestamp': event.timestamp.isoformat(),
            'IP Address': event.ip_address,
            'User Agent': event.user_agent
        })
    
    df_proctoring = pd.DataFrame(proctoring_data)
    df_proctoring.to_excel(writer, sheet_name='Proctoring Events', index=False)
    
    writer.close()
    output.seek(0)
    
    return output

def export_candidate_report(candidate_id: int, assessment_id: int, db: Session) -> io.BytesIO:
    """Export detailed report for a specific candidate"""
    
    assessment_candidate = db.query(AssessmentCandidate).filter(
        AssessmentCandidate.candidate_id == candidate_id,
        AssessmentCandidate.assessment_id == assessment_id
    ).first()
    
    if not assessment_candidate:
        return io.BytesIO()
    
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')
    
    # Candidate summary
    candidate = assessment_candidate.candidate
    assessment = assessment_candidate.assessment
    
    summary_data = [{
        'Assessment': assessment.title,
        'Candidate Name': candidate.name,
        'Email': candidate.email,
        'Position': candidate.position,
        'Status': assessment_candidate.status.value,
        'Started At': assessment_candidate.started_at.isoformat() if assessment_candidate.started_at else '',
        'Submitted At': assessment_candidate.submitted_at.isoformat() if assessment_candidate.submitted_at else '',
        'Total Score': assessment_candidate.total_score,
        'Percentage Score': assessment_candidate.percentage_score,
        'Passing Status': 'PASS' if assessment_candidate.percentage_score >= assessment.passing_score else 'FAIL'
    }]
    
    df_summary = pd.DataFrame(summary_data)
    df_summary.to_excel(writer, sheet_name='Summary', index=False)
    
    # Question-wise performance
    submissions = db.query(Submission).filter(
        Submission.candidate_id == candidate_id,
        Submission.assessment_id == assessment_id,
        Submission.is_final_submission == True
    ).all()
    
    performance_data = []
    for submission in submissions:
        question_title = "Unknown"
        for aq in assessment.assessment_questions:
            if aq.question_id == submission.question_id:
                question_title = aq.question.title
                break
        
        performance_data.append({
            'Question': question_title,
            'Language': submission.language,
            'Score': submission.total_score,
            'Verdict': submission.overall_verdict.value if submission.overall_verdict else '',
            'Execution Time (ms)': submission.execution_time_ms,
            'Test Cases Passed': len([r for r in submission.results if r.verdict.value == 'OK']),
            'Total Test Cases': len(submission.results)
        })
    
    df_performance = pd.DataFrame(performance_data)
    df_performance.to_excel(writer, sheet_name='Performance', index=False)
    
    writer.close()
    output.seek(0)
    
    return output