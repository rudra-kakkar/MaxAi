import asyncio
import configparser
from datetime import date, timedelta, datetime
import requests
import json
import time
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

# List of users, their expected email subjects, and the days they should send emails
EXPECTED_EMAILS = [
    {"name": "Rudra", "email": "rudra.kakkar@kochiva.com", "subject": "Daily Report - Rudra", "day": "Thursday"},
    # {"name": "corp", "email": "corp@kochartech.com", "subject": "Daily Report - Corp", "day": "Tuesday"},
]

# Dictionary to store delay times
delay_tracker = {"rudra.kakkar@kochiva.com":2}

def get_today_emails():
    """Filter expected emails based on today's weekday."""
    today = date.today().strftime('%A')  # Get the current weekday
    return [email for email in EXPECTED_EMAILS if email["day"] == today]

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

async def check_emails_for_subjects(graph: Graph, check_date, expected_emails):
    """
    Check the inbox for specific emails with expected subjects on a given date.
    Returns a list of users who haven't sent an email with the expected subject and updates delay tracker.
    """
    message_page = await graph.get_inbox()
    if message_page and message_page.value:
        users_who_sent_emails = {}

        for message in message_page.value:
            if (
                message.from_ and message.from_.email_address and 
                message.subject and 
                message.received_date_time.date() >= check_date
            ):
                sender_email = message.from_.email_address.address.lower()
                subject = message.subject.lower()
                received_time = message.received_date_time
                
                for expected in expected_emails:
                    if sender_email == expected["email"].lower() and expected["subject"].lower() in subject:
                        users_who_sent_emails[sender_email] = received_time

        users_to_remind = []
        for user in expected_emails:
            email = user["email"].lower()
            if email not in users_who_sent_emails:
                delay_tracker[email] = delay_tracker.get(email, 0) + 1
                users_to_remind.append(user)
            else:
                delay_tracker.pop(email, None)  # Remove from delay tracker if mail is received

        return users_to_remind
    else:
        print("No messages found in inbox.")
        for user in expected_emails:
            delay_tracker[user["email"].lower()] = delay_tracker.get(user["email"].lower(), 0) + 1
        return expected_emails

async def send_reminder_or_alert(graph: Graph, user):
    """Send a reminder or an alert email based on delay time."""
    delay_days = delay_tracker.get(user["email"].lower(), 0)
    current_date = date.today()
    
    if delay_days > 1:
        subject = f"ALERT: Urgent Report Missing - {current_date}"
        prompt = f"Write an urgent alert email to {user['name']} about missing their report for {delay_days} days."
    else:
        subject = f"Reminder: Send Your Daily Report - {current_date}"
        prompt = f"Write a professional reminder email to {user['name']} to send their report. This is a {delay_days}-day delay reminder."
    
    body = await send_request_to_llm(prompt, f"User: {user['name']}, Date: {current_date}, Delay: {delay_days} days")
    await graph.send_mail(subject, body, user["email"])
    print(f"{'Alert' if delay_days > 1 else 'Reminder'} sent to {user['name']} at {user['email']}, Delay: {delay_days} days")

async def main():
    """Main function to check for emails with specific subjects and send reminders or alerts until received."""
    print('Python Email Checker with AI Agent\n')
    while True:
        try:
            check_date = date.today()
            today_expected_emails = get_today_emails()
            users_to_remind = await check_emails_for_subjects(graph, check_date, today_expected_emails)
            
            if users_to_remind:
                print("Sending notifications to the following users:")
                for user in users_to_remind:
                    print(f"- {user['name']} ({user['email']})")
                    await send_reminder_or_alert(graph, user)
            else:
                print("All required emails with expected subjects have been received. No notifications needed.")
            
            await asyncio.sleep(30)  # Wait for a day before checking again
        except Exception as e:
            print(f"An error occurred: {e}")
            time.sleep(10)  # Short delay before retrying in case of an error

if __name__ == "__main__":
    while True:
        try:
            asyncio.run(main())
        except Exception as e:
            print(f"Main process crashed: {e}, restarting...")
            time.sleep(10)  # Short delay before restarting
