"""
FastMCP Gmail Reader Server with Extended Draft and Email Fetching
"""

from fastmcp import FastMCP
from typing import List, Optional
import os
import pickle
import time
import base64
import re
from email.mime.text import MIMEText

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError


# ✅ Create server
mcp = FastMCP("Gmail Reader Extended")


# ✅ Gmail API setup
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.modify'
]

script_dir = os.path.dirname(os.path.abspath(__file__))
credentials_path = os.path.join(script_dir, 'credentials.json')
token_path = os.path.join(script_dir, 'token.pickle')


def get_gmail_service():
    creds = None
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
    service = build('gmail', 'v1', credentials=creds)
    return service


def safe_api_call(func, *args, **kwargs):
    for n in range(5):
        try:
            return func(*args, **kwargs)
        except HttpError as error:
            if error.resp.status == 429:
                wait_time = (2 ** n)
                print(f"Rate limited. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                raise error
    raise Exception("API rate limit hit too many times")


# ✅ Email reading MCP tool with page token for "load more"
@mcp.tool
def read_emails(max_results: int = 5, page_token: Optional[str] = None) -> dict:
    """
    Fetch recent emails from Gmail inbox.

    Args:
        max_results: Number of emails to fetch.
        page_token: Optional page token to fetch next batch.

    Returns:
        Dictionary containing:
            - email_list: List of email summaries.
            - nextPageToken: Token to retrieve more emails if available.
    """
    service = get_gmail_service()

    results = safe_api_call(
        service.users().messages().list,
        userId='me',
        labelIds=['INBOX'],
        maxResults=max_results,
        pageToken=page_token
    ).execute()

    messages = results.get('messages', [])
    next_page_token = results.get('nextPageToken')
    email_list = []

    for message in messages:
        msg = safe_api_call(
            service.users().messages().get,
            userId='me',
            id=message['id'],
            format='metadata',
            metadataHeaders=['From', 'Subject']
        ).execute()

        headers = msg.get('payload', {}).get('headers', [])
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
        snippet = msg.get('snippet', 'No Snippet')

        email_list.append({
            'id': message['id'],
            'subject': subject,
            'sender': sender,
            'snippet': snippet
        })

    return {
        'email_list': email_list,
        'nextPageToken': next_page_token or None
    }


# ✅ Draft creation: reply to an email
@mcp.tool
def create_reply_draft(email_id: str, reply_text: str) -> str:
    """
    Create a reply draft for an email with the given reply text.

    Args:
        email_id: The ID of the email to reply to.
        reply_text: The text content of the reply.

    Returns:
        A status message about the draft creation.
    """
    service = get_gmail_service()

    try:
        # Fetch the full email data
        msg = safe_api_call(
            service.users().messages().get,
            userId='me',
            id=email_id,
            format='full'
        ).execute()

        headers = msg.get('payload', {}).get('headers', [])
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        raw_sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
        match = re.search(r'<(.+?)>', raw_sender)
        sender = match.group(1) if match else raw_sender.strip()
        thread_id = msg.get('threadId', None)

        # Create the MIME email
        message = MIMEText(reply_text)
        message['to'] = sender
        message['subject'] = f"Re: {subject}"
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        draft_body = {'message': {'raw': raw}}
        if thread_id:
            draft_body['message']['threadId'] = thread_id

        safe_api_call(
            service.users().drafts().create,
            userId='me',
            body=draft_body
        ).execute()

        return f"✅ Draft reply to '{subject}' created for {sender}."

    except Exception as e:
        return f"❌ Failed to create reply draft: {str(e)}"


# ✅ Draft creation: new email (no sender required)
@mcp.tool
def create_new_email_draft(
    recipient: Optional[str] = "",
    subject: Optional[str] = "No Subject",
    body_text: Optional[str] = ""
) -> str:
    """
    Create a new draft email (not a reply).

    Args:
        recipient: Email address to send to (can be empty to leave blank).
        subject: Subject of the email.
        body_text: Body content of the email.

    Returns:
        A status message about the draft creation.
    """
    service = get_gmail_service()

    try:
        message = MIMEText(body_text)
        if recipient:
            message['to'] = recipient
        message['subject'] = subject

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        draft_body = {'message': {'raw': raw}}

        safe_api_call(
            service.users().drafts().create,
            userId='me',
            body=draft_body
        ).execute()

        return f"✅ New draft created (to: {recipient or '[No recipient]'}, subject: {subject})."

    except Exception as e:
        return f"❌ Failed to create new email draft: {str(e)}"


# ✅ Run MCP Server
if __name__ == "__main__":
    mcp.run()
