import os
import json
import logging
from typing import Optional
from io import BytesIO
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
from app.core.config import settings

logger = logging.getLogger(__name__)

class GoogleDriveBackup:
    """Service for backing up files to Google Drive"""
    
    def __init__(self):
        self.service = None
        self.folder_id = settings.GOOGLE_DRIVE_FOLDER_ID
        
        if settings.GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON and self.folder_id:
            try:
                # Parse service account JSON
                service_account_info = json.loads(settings.GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON)
                
                # Create credentials
                credentials = service_account.Credentials.from_service_account_info(
                    service_account_info,
                    scopes=['https://www.googleapis.com/auth/drive.file']
                )
                
                # Build service
                self.service = build('drive', 'v3', credentials=credentials)
                logger.info("Google Drive backup service initialized")
                
            except Exception as e:
                logger.error(f"Failed to initialize Google Drive service: {e}")
                self.service = None
    
    def is_enabled(self) -> bool:
        """Check if Google Drive backup is enabled and configured"""
        return self.service is not None and self.folder_id
    
    def upload_file(self, file_content: bytes, filename: str, mime_type: str = 'application/octet-stream') -> Optional[str]:
        """Upload a file to Google Drive"""
        if not self.is_enabled():
            logger.warning("Google Drive backup not configured")
            return None
        
        try:
            # Create file metadata
            file_metadata = {
                'name': filename,
                'parents': [self.folder_id]
            }
            
            # Create media upload
            media = MediaIoBaseUpload(
                BytesIO(file_content),
                mimetype=mime_type,
                resumable=True
            )
            
            # Upload file
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            file_id = file.get('id')
            logger.info(f"Successfully uploaded {filename} to Google Drive (ID: {file_id})")
            return file_id
            
        except Exception as e:
            logger.error(f"Failed to upload {filename} to Google Drive: {e}")
            return None
    
    def backup_assessment_results(self, assessment_id: int, csv_content: str, excel_content: bytes) -> dict:
        """Backup assessment results to Google Drive"""
        results = {
            'csv_file_id': None,
            'excel_file_id': None,
            'success': False
        }
        
        if not self.is_enabled():
            return results
        
        try:
            # Upload CSV
            csv_filename = f"assessment_{assessment_id}_results.csv"
            csv_file_id = self.upload_file(
                csv_content.encode('utf-8'),
                csv_filename,
                'text/csv'
            )
            results['csv_file_id'] = csv_file_id
            
            # Upload Excel
            excel_filename = f"assessment_{assessment_id}_results.xlsx"
            excel_file_id = self.upload_file(
                excel_content,
                excel_filename,
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            results['excel_file_id'] = excel_file_id
            
            results['success'] = bool(csv_file_id or excel_file_id)
            
        except Exception as e:
            logger.error(f"Failed to backup assessment {assessment_id} results: {e}")
        
        return results

# Global instance
google_drive_backup = GoogleDriveBackup()