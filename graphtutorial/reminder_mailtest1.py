import asyncio
import configparser
from datetime import date, timedelta
import requests
import json
from graph import Graph

API_URL = "http://app.knowmax.in/v1/completion-messages"
HEADERS = {
    "Authorization": "Bearer app-Y6s7hruAKBs6VDrC3V9xE3wA",  # Replace with actual API key
    "Content-Type": "application/json"
}

# Load settings
config = configparser.ConfigParser()
config.read(['config.cfg', 'config.dev.cfg'])
azure_settings = config['azure']
graph = Graph(azure_settings)

# List of users and their expected email subjects
EXPECTED_EMAILS = [
    {"name": "Rudra", "email": "rudra.kakkar@kochiva.com", "subject": "Daily Report"}
]

async def send_request_to_llm(query_prompt, table_data):
    """Send a request to the LLM and return the combined answers."""
    payload = {
        "inputs": {
            "query": query_prompt,
            "table": table_data,
        },
        "response_mode": "streaming",
        "user": "abc-123"
    }
    response = requests.post(API_URL, json=payload, headers=HEADERS)
    if response.status_code == 200:
        return extract_answers_from_response(response.text)
    else:
        print(f"Failed to send data. Status code: {response.status_code}, Error: {response.text}")
        return ""


def extract_answers_from_response(response_text):
    """Extract answers from API response text."""
    answers = []
    for line in response_text.splitlines():
        line = line.lstrip("data: ").strip()
        if not line:
            continue
        try:
            line_data = json.loads(line)
            answer = line_data.get("answer")
            if answer:
                answers.append(answer)
        except json.JSONDecodeError:
            print("Failed to decode line:", line)
    return " ".join(answers)

async def check_emails_for_subjects(graph: Graph):
    """
    Check the inbox for specific emails with expected subjects.
    Returns a list of users who haven't sent an email with the expected subject.
    """
    current_date = date.today()
    last_expected_date = current_date - timedelta(days=2)
    
    # Fetch the inbox
    message_page = await graph.get_inbox()
    if message_page and message_page.value:
        # Create a set of users who have sent emails with expected subjects
        users_who_sent_emails = set()

        for message in message_page.value:
            if (
                message.from_ and message.from_.email_address and 
                message.subject and 
                message.received_date_time.date() >= last_expected_date
            ):
                sender_email = message.from_.email_address.address.lower()
                subject = message.subject.lower()
                
                for expected in EXPECTED_EMAILS:
                    if sender_email == expected["email"].lower() and expected["subject"].lower() in subject:
                        users_who_sent_emails.add(sender_email)

        # Check which users haven't sent the expected emails
        users_to_remind = [
            user for user in EXPECTED_EMAILS if user["email"].lower() not in users_who_sent_emails
        ]
        return users_to_remind
    else:
        print("No messages found in inbox.")
        return []

async def send_reminder(graph: Graph, user):
    """Send a reminder email to a user who hasn't sent their expected report."""
    print(user)
    prompt = f"You have to Write a personlize email to the given person given below and ask why you have not sent the mail."
    current_date = date.today()
    subject = f"Reminder: Send Your Daily Report - {current_date}"
    body = await send_request_to_llm(prompt, f"User: {user['name']}, Date: {current_date}, Subject : {user["subject"]}")

    await graph.send_mail(subject, body, user["email"])
    print(f"Reminder sent to {user['name']} at {user['email']}")

async def main():
    """Main function to check for emails with specific subjects and send reminders."""
    print('Python Email Checker with AI Agent\n')
    users_to_remind = await check_emails_for_subjects(graph)

    if users_to_remind:
        print("Sending reminders to the following users:")
        for user in users_to_remind:
            print(f"- {user['name']} ({user['email']})")
            await send_reminder(graph, user)
    else:
        print("All required emails with expected subjects have been received. No reminders needed.")

if __name__ == "__main__":
    asyncio.run(main())
