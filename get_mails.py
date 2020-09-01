from prompt_toolkit import prompt
from app.service import GmailService


if __name__ == '__main__':

    service = GmailService()
    matches = service.list_emails(100)
    for match in matches:
        print(service.fetch_email(match))
