import requests
import base64
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from typing import Dict, Any

class GoogleApiAdapter:

    def __init__(self, client_id: str, client_secret: str, rbac_proxy_url: str, rbac_token: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.rbac_proxy_url = rbac_proxy_url
        self.rbac_token = rbac_token
        self._init_authentication_context()

    def _init_authentication_context(self):
        url = f"{self.rbac_proxy_url}/token/google"
        r = requests.get(url, headers={"Authorization": f"Bearer {self.rbac_token}"})
        self.access_token = r.json().get("access_token")
        self.token_expiration = r.json().get("expiration_time")
        self.headers = {"Authorization": f"Bearer {self.access_token}"}

    def get_profile(self, user_context: Dict[str, Any] = None):
        user_scopes = user_context.get('scopes', []) if user_context else []
        
        has_read_access = any(
            scope in ['api:google:*', 'api:google:read']
            for scope in user_scopes
        )
        
        if not has_read_access:
            raise Exception("Insufficient permissions to read google profile")
            
        url = "https://openidconnect.googleapis.com/v1/userinfo"
        r = requests.get(url, headers=self.headers)
        return r.json()

    def list_files(self, page_size=10, user_context: Dict[str, Any] = None):
        user_scopes = user_context.get('scopes', []) if user_context else []
        
        has_read_access = any(
            scope in ['api:google:*', 'api:google:read']
            for scope in user_scopes
        )
        
        if not has_read_access:
            raise Exception("Insufficient permissions to read google drive")
            
        url = "https://www.googleapis.com/drive/v3/files"
        params = {"pageSize": page_size, "fields": "files(id,name)"}
        r = requests.get(url, headers=self.headers, params=params)
                
        return r.json().get("files", [])

    def list_emails(self, max_results=10, user_context: Dict[str, Any] = None):
        user_scopes = user_context.get('scopes', []) if user_context else []
        
        has_read_access = any(
            scope in ['api:google:*', 'api:google:read']
            for scope in user_scopes
        )
        
        if not has_read_access:
            raise Exception("Insufficient permissions to read google emails")
            
        # Step 1: Get list of message IDs
        list_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
        params = {"maxResults": max_results}
        r = requests.get(list_url, headers=self.headers, params=params)
        
        message_ids = r.json().get("messages", [])
        
        # Step 2: Fetch full details for each message
        detailed_messages = []
        for msg in message_ids:
            msg_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg['id']}"
            msg_params = {
                "format": "metadata",
                "metadataHeaders": "From,Subject,Date"  # Try as comma-separated string
            }
            msg_response = requests.get(msg_url, headers=self.headers, params=msg_params)
            
            if msg_response.status_code == 200:
                detailed_messages.append(msg_response.json())
            else:
                # Fallback: at least include the ID
                detailed_messages.append(msg)
    
        return detailed_messages

    def list_calendars(self, user_context: Dict[str, Any] = None):
        user_scopes = user_context.get('scopes', []) if user_context else []
      
        has_read_access = any(
            scope in ['api:google:*', 'api:google:read']
            for scope in user_scopes
        )
        
        if not has_read_access:
            raise Exception("Insufficient permissions to read google calendars")
            
        url = "https://www.googleapis.com/calendar/v3/users/me/calendarList"
        r = requests.get(url, headers=self.headers)

        return r.json().get("items", [])

    def create_calendar(self, summary="New Calendar", user_context: Dict[str, Any] = None):
        user_scopes = user_context.get('scopes', []) if user_context else []
        
        has_write_access = any(
            scope in ['api:google:*']
            for scope in user_scopes
        )
        
        if not has_write_access:
            raise Exception("Insufficient permissions to create google calendar")
            
        url = "https://www.googleapis.com/calendar/v3/calendars"
        body = {"summary": summary, "timeZone": "UTC"}
        r = requests.post(url, headers={**self.headers, "Content-Type": "application/json"}, json=body)
        
        return r.json()

    def remove_calendar(self, calendar_id, user_context: Dict[str, Any] = None):
        user_scopes = user_context.get('scopes', []) if user_context else []
        
        has_write_access = any(
            scope in ['api:google:*']
            for scope in user_scopes
        )
        
        if not has_write_access:
            raise Exception("Insufficient permissions to remove google calendar")
            
        url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}"
        r = requests.delete(url, headers=self.headers)

        return {"status": r.status_code, "calendarId": calendar_id}

    def list_events(self, calendar_id="primary", max_results=10, user_context: Dict[str, Any] = None):
      user_scopes = user_context.get('scopes', []) if user_context else []
      
      has_read_access = any(
          scope in ['api:google:*', 'api:google:read']
          for scope in user_scopes
      )
      
      if not has_read_access:
          raise Exception("Insufficient permissions to read google events")
          
      url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
      params = {
          "maxResults": max_results,
          "singleEvents": True,
          "orderBy": "startTime",
          "timeMin": datetime.now(timezone.utc).isoformat()
      }
      r = requests.get(url, headers=self.headers, params=params)

      return r.json().get("items", [])

    def create_event(self, calendar_id="primary", summary="Test Event", start_time=None, end_time=None, description="", user_context: Dict[str, Any] = None):
      """
      Create a new event in the given calendar.
      :param calendar_id: which calendar (default = primary)
      :param summary: event title
      :param start_time: ISO 8601 datetime string, e.g. "2025-10-02T10:00:00Z"
      :param end_time: ISO 8601 datetime string, e.g. "2025-10-02T11:00:00Z"
      :param description: optional description
      """
      
      user_scopes = user_context.get('scopes', []) if user_context else []
      
      has_write_access = any(
          scope in ['api:google:*']
          for scope in user_scopes
      )
      
      if not has_write_access:
          raise Exception("Insufficient permissions to create google event")
          
      if not start_time or not end_time:
          raise ValueError("start_time and end_time are required")

      url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
      body = {
          "summary": summary,
          "description": description,
          "start": {"dateTime": start_time, "timeZone": "UTC"},
          "end": {"dateTime": end_time, "timeZone": "UTC"}
      }
      r = requests.post(url, headers={**self.headers, "Content-Type": "application/json"}, json=body)
      
      return r.json()

    def send_email(self, to, subject, body_text, user_context: Dict[str, Any] = None):
        user_scopes = user_context.get('scopes', []) if user_context else []
        
        has_write_access = any(
            scope in ['api:google:*']
            for scope in user_scopes
        )
        
        if not has_write_access:
            raise Exception("Insufficient permissions to send google email")
            
        url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
        message = MIMEText(body_text)
        message["to"] = to
        message["subject"] = subject

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        send_body = {"raw": raw_message}

        r = requests.post(url, headers={**self.headers, "Content-Type": "application/json"}, json=send_body)
        
        return r.json()
