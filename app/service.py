import os
import pickle
import base64
import dateutil.parser as parser
from app.utils import double_quoted
from bs4 import BeautifulSoup
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

FIN_WORDS = ['transaction', 'statement', 'bill', 'account statement', 'subscription', 'receipt', 'bank statement']
SUBJECT_QUERY = ' OR '.join([double_quoted(x) for x in FIN_WORDS])
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


class GmailService:
    credentials = None
    message_api = None

    def __init__(self):
        # Checks for pickle file
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                self.credentials = pickle.load(token)

        # Validate credentials
        if not self.credentials or not self.credentials.valid:
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())
            else:
                # Launch the default browser for generating token
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                self.credentials = flow.run_local_server(port=0)

        # Save the credentials for next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(self.credentials, token)

        self.message_api = build('gmail', 'v1', credentials=self.credentials).users().messages()

    def list_emails(self, max_results: int):
        a = self.message_api.list(userId='me', maxResults=max_results,
                                     q='subject:({})'.format(SUBJECT_QUERY)).execute()
        return [x['id'] for x in a['messages']]

    def fetch_email(self, message_id):
        message = self.message_api.get(userId='me', id=message_id).execute()
        res = self.parse_message(message)
        res['attachments'] = self.parse_attachment(message, message_id)
        return res

    @staticmethod
    def parse_message(message):
        msg_res = {}
        payload = message['payload']
        headers = payload['headers']
        # getting the Subject, Date, From
        for h in headers:
            if h['name'] == 'Subject':
                msg_res['Subject'] = h['value']
            elif h['name'] == 'Date':
                date_parse = (parser.parse(h['value']))
                msg_res['Date'] = str(date_parse.date())
            elif h['name'] == 'From':
                msg_res['Sender'] = h['value']
            else:
                pass
        msg_res['Snippet'] = message['snippet']
        return msg_res

    def parse_attachment(self, message, message_id) -> str:
        for part in message['payload']['parts']:
            if part['filename']:
                if 'data' in part['body']:
                    data = part['body']['data']
                else:
                    att_id = part['body']['attachmentId']
                    att_res = self.message_api.attachments().get(userId='me', messageId=message_id,
                                                                 id=att_id).execute()
                    data = att_res['data']
                file_data = base64.urlsafe_b64decode(data)
                path = part['filename'] + '_{}'.format(message_id)

                with open(path, 'w') as f:
                    f.write(file_data.decode('utf-8'))
                return path
        return ''
