import subprocess
import tempfile
import os
import time
import signal
from typing import Dict, Any, List, Tuple
import logging
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.submission import Submission, SubmissionResult, SubmissionStatus, VerdictType
from app.models.question import TestCase
from app.core.config import settings

logger = logging.getLogger(__name__)

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Code execution timed out")

class CodeExecutor:
    """Handles secure code execution in various languages"""
    
    LANGUAGE_CONFIGS = {
        "python": {
            "extension": ".py",
            "compile_command": None,
            "run_command": ["python3", "{filename}"],
            "timeout": settings.CODE_EXECUTION_TIMEOUT
        },
        "cpp": {
            "extension": ".cpp",
            "compile_command": ["g++", "-o", "{executable}", "{filename}", "-std=c++17"],
            "run_command": ["./{executable}"],
            "timeout": settings.CODE_EXECUTION_TIMEOUT
        },
        "c": {
            "extension": ".c",
            "compile_command": ["gcc", "-o", "{executable}", "{filename}"],
            "run_command": ["./{executable}"],
            "timeout": settings.CODE_EXECUTION_TIMEOUT
        },
        "java": {
            "extension": ".java",
            "compile_command": ["javac", "{filename}"],
            "run_command": ["java", "{classname}"],
            "timeout": settings.CODE_EXECUTION_TIMEOUT
        }
    }
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        
    def cleanup(self):
        """Clean up temporary files"""
        import shutil
        try:
            shutil.rmtree(self.temp_dir)
        except Exception as e:
            logger.warning(f"Failed to cleanup temp directory: {e}")
    
    def execute_code(self, code: str, language: str, input_data: str, 
                    time_limit: int = None, memory_limit: int = None) -> Dict[str, Any]:
        """Execute code with given input and return results"""
        
        if language not in self.LANGUAGE_CONFIGS:
            return {
                "verdict": VerdictType.CE,
                "output": "",
                "error": f"Unsupported language: {language}",
                "execution_time_ms": 0,
                "memory_used_kb": 0
            }
        
        config = self.LANGUAGE_CONFIGS[language]
        time_limit = time_limit or config["timeout"]
        memory_limit = memory_limit or settings.CODE_EXECUTION_MEMORY_LIMIT
        
        try:
            # Create source file
            source_file = os.path.join(self.temp_dir, f"solution{config['extension']}")
            with open(source_file, 'w') as f:
                f.write(code)
            
            # Compile if necessary
            executable = None
            if config["compile_command"]:
                if language == "java":
                    # Extract class name for Java
                    class_name = self._extract_java_class_name(code)
                    if not class_name:
                        return {
                            "verdict": VerdictType.CE,
                            "output": "",
                            "error": "No public class found in Java code",
                            "execution_time_ms": 0,
                            "memory_used_kb": 0
                        }
                    source_file = os.path.join(self.temp_dir, f"{class_name}.java")
                    with open(source_file, 'w') as f:
                        f.write(code)
                
                executable = os.path.join(self.temp_dir, "solution")
                compile_cmd = [
                    arg.format(filename=source_file, executable=executable, classname=class_name if language == "java" else "solution")
                    for arg in config["compile_command"]
                ]
                
                compile_result = subprocess.run(
                    compile_cmd,
                    cwd=self.temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if compile_result.returncode != 0:
                    return {
                        "verdict": VerdictType.CE,
                        "output": "",
                        "error": compile_result.stderr,
                        "execution_time_ms": 0,
                        "memory_used_kb": 0
                    }
            
            # Execute code
            run_cmd = [
                arg.format(filename=source_file, executable="solution", classname=class_name if language == "java" else "solution")
                for arg in config["run_command"]
            ]
            
            start_time = time.time()
            
            try:
                process = subprocess.Popen(
                    run_cmd,
                    cwd=self.temp_dir,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                try:
                    stdout, stderr = process.communicate(
                        input=input_data,
                        timeout=time_limit
                    )
                    execution_time_ms = int((time.time() - start_time) * 1000)
                    
                    if process.returncode != 0:
                        return {
                            "verdict": VerdictType.RTE,
                            "output": stdout,
                            "error": stderr,
                            "execution_time_ms": execution_time_ms,
                            "memory_used_kb": 0  # Memory monitoring would require more complex setup
                        }
                    
                    return {
                        "verdict": VerdictType.OK,
                        "output": stdout.strip(),
                        "error": stderr,
                        "execution_time_ms": execution_time_ms,
                        "memory_used_kb": 0
                    }
                    
                except subprocess.TimeoutExpired:
                    process.kill()
                    return {
                        "verdict": VerdictType.TLE,
                        "output": "",
                        "error": "Time limit exceeded",
                        "execution_time_ms": time_limit * 1000,
                        "memory_used_kb": 0
                    }
                
            except Exception as e:
                return {
                    "verdict": VerdictType.RTE,
                    "output": "",
                    "error": str(e),
                    "execution_time_ms": 0,
                    "memory_used_kb": 0
                }
                
        except Exception as e:
            logger.error(f"Code execution error: {e}")
            return {
                "verdict": VerdictType.RTE,
                "output": "",
                "error": str(e),
                "execution_time_ms": 0,
                "memory_used_kb": 0
            }
    
    def _extract_java_class_name(self, code: str) -> str:
        """Extract public class name from Java code"""
        import re
        pattern = r'public\s+class\s+(\w+)'
        match = re.search(pattern, code)
        return match.group(1) if match else "Solution"

def execute_code_async(submission_id: int, run_type: str = "test"):
    """Async function to execute code for a submission (used by RQ worker)"""
    db: Session = SessionLocal()
    executor = CodeExecutor()
    
    try:
        # Get submission
        submission = db.query(Submission).filter(Submission.id == submission_id).first()
        if not submission:
            logger.error(f"Submission {submission_id} not found")
            return
        
        # Update status to running
        submission.status = SubmissionStatus.RUNNING
        db.commit()
        
        # Get question and test cases
        question = None
        for aq in submission.candidate.assessment_candidates[0].assessment.assessment_questions:
            if aq.question_id == submission.question_id:
                question = aq.question
                break
        
        if not question:
            submission.status = SubmissionStatus.ERROR
            submission.runtime_error = "Question not found"
            db.commit()
            return
        
        # Get test cases (public for testing, all for submission)
        if run_type == "test":
            test_cases = [tc for tc in question.test_cases if tc.is_public]
        else:
            test_cases = question.test_cases
        
        if not test_cases:
            submission.status = SubmissionStatus.ERROR
            submission.runtime_error = "No test cases found"
            db.commit()
            return
        
        # Execute against each test case
        total_score = 0.0
        total_weight = sum(tc.weight for tc in test_cases)
        overall_verdict = VerdictType.OK
        
        for test_case in test_cases:
            result = executor.execute_code(
                submission.code,
                submission.language,
                test_case.input_data,
                test_case.time_limit_seconds,
                test_case.memory_limit_mb
            )
            
            # Determine verdict and score
            verdict = result["verdict"]
            score = 0.0
            
            if verdict == VerdictType.OK:
                # Check if output matches expected output
                expected = test_case.expected_output.strip()
                actual = result["output"].strip()
                
                if expected == actual:
                    score = (test_case.weight / total_weight) * question.max_score
                else:
                    verdict = VerdictType.WA
            
            # Update overall verdict (worst case)
            if verdict != VerdictType.OK:
                overall_verdict = verdict
            
            total_score += score
            
            # Save test case result
            submission_result = SubmissionResult(
                submission_id=submission.id,
                test_case_id=test_case.id,
                verdict=verdict,
                execution_time_ms=result["execution_time_ms"],
                memory_used_kb=result["memory_used_kb"],
                score=score,
                actual_output=result["output"],
                error_message=result["error"]
            )
            db.add(submission_result)
        
        # Update submission
        submission.status = SubmissionStatus.COMPLETED
        submission.overall_verdict = overall_verdict
        submission.total_score = total_score
        submission.executed_at = submission.submitted_at
        
        db.commit()
        
        # Update assessment candidate score if this is a final submission
        if submission.is_final_submission:
            from app.services.candidate_service import calculate_assessment_score
            assessment_candidate = db.query(AssessmentCandidate).filter(
                AssessmentCandidate.candidate_id == submission.candidate_id,
                AssessmentCandidate.assessment_id == submission.assessment_id
            ).first()
            
            if assessment_candidate:
                calculate_assessment_score(assessment_candidate, db)
        
        logger.info(f"Code execution completed for submission {submission_id}")
        
    except Exception as e:
        logger.error(f"Error executing code for submission {submission_id}: {e}")
        if submission:
            submission.status = SubmissionStatus.ERROR
            submission.runtime_error = str(e)
            db.commit()
    
    finally:
        executor.cleanup()
        db.close()