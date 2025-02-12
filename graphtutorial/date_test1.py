import asyncio
import configparser
from datetime import date, timedelta
import requests
import json
import time
import mysql.connector
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

# MySQL Database Connection
db_config = {
    "host": "localhost",
    "user": "myuser",
    "password": "mypassword",
    "database": "mails"
}

# Manual date override for testing
TEST_DATE = None  # Set to None for production, or use a specific date like date(2023, 10, 26)

def get_current_date():
    """Return the current date or the test date if specified."""
    return TEST_DATE if TEST_DATE else date.today()

def connect_db():
    return mysql.connector.connect(**db_config)

def get_pending_emails():
    """Fetch emails with expected_date less than or equal to the current/test date."""
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT user_name, email, subject, expected_date, frequency FROM emails WHERE expected_date <= %s", (get_current_date(),))
    emails = cursor.fetchall()
    
    conn.close()
    return emails

def update_expected_date(email, expected_date, frequency):
    """Update the expected_date for recurring emails based on the original expected_date."""
    if frequency:
        new_expected_date = expected_date + timedelta(days=frequency)
        query = """
            UPDATE emails 
            SET expected_date = %s 
            WHERE email = %s
        """
        values = (new_expected_date.strftime('%Y-%m-%d'), email)

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute(query, values)
        conn.commit()
        conn.close()

import re

async def check_emails_for_subjects(graph: Graph, pending_emails):
    """Check inbox for pending emails and return a list of missing ones."""
    message_page = await graph.get_inbox()
    users_who_sent_emails = set()

    if message_page and message_page.value:
        for message in message_page.value:
            if message.from_ and message.from_.email_address and message.subject and message.received_date_time:
                sender_email = message.from_.email_address.address.lower()
                subject = message.subject.lower()
                received_date = message.received_date_time.date()  # Convert to date object

                for expected in pending_emails:
                    expected_email = expected["email"].lower()
                    expected_subject = expected["subject"].lower()
                    expected_date = expected["expected_date"]

                    # Convert expected_date to date object if it's a string
                    if isinstance(expected_date, str):
                        expected_date = date.fromisoformat(expected_date)

                    # Create a regex pattern to match the subject and expected date
                    # Example: If subject is "Daily Report" and expected_date is 2023-10-26,
                    # the regex will match "Daily Report 2023-10-26"
                    date_str = expected_date.strftime('%Y-%m-%d')  # Format date as YYYY-MM-DD
                    pattern = re.compile(rf"{re.escape(expected_subject)}.*{re.escape(date_str)}", re.IGNORECASE)

                    # Check if the email matches the sender, regex pattern, and is received on or after expected_date
                    if (
                        sender_email == expected_email
                        and pattern.search(subject)  # Use regex to match subject and date
                        and received_date >= expected_date  # Only update if received on or after expected_date
                    ):
                        users_who_sent_emails.add(sender_email)

                        # **Update expected_date only for new emails**
                        update_expected_date(sender_email, expected_date, expected["frequency"])
                        print(f"✅ Updated expected date for {sender_email} (Received: {received_date})")

    users_to_notify = []
    for user in pending_emails:
        email = user["email"].lower()
        expected_date = user["expected_date"]

        if isinstance(expected_date, str):
            expected_date = date.fromisoformat(expected_date)

        delay_days = (get_current_date() - expected_date).days  # Calculate delay

        # If the user has NOT sent the email, add them to notify list
        if email not in users_who_sent_emails:
            users_to_notify.append({**user, "delay_days": delay_days})

    return users_to_notify


async def send_reminder(graph: Graph, user):
    """Send a reminder email if the delay is 0 days."""
    subject = f"MAX AI Reminder: Please share your report -{user['subject']}-{get_current_date()}"
    expected_date = user["expected_date"]
    if isinstance(expected_date, str):
        expected_date = date.fromisoformat(expected_date)
    
    # Include subject and expected date in the prompt
    prompt = (
        f"Write a mail according to given data without providing any additional suggestions or anything else. Dont add subject"
        f"Dear {user['user_name']}, this is a reminder to send your required report titled "
        f"'{user['subject']}' for {expected_date.strftime('%Y-%m-%d')}. "
        f"Please ensure it is submitted today. "
        f"Regards, MAX AI"
    )

    body = await send_request_to_llm(prompt, user)
    await graph.send_mail(subject, body, user["email"])
    print(f"Reminder email sent to {user['user_name']} at {user['email']} (Delay: 0 days)")


async def send_alert(graph: Graph, user):
    """Send an alert email if the delay is greater than 0 days."""
    delay_days = user.get("delay_days", 0)
    expected_date = user["expected_date"]
    if isinstance(expected_date, str):
        expected_date = date.fromisoformat(expected_date)

    subject = f"Max AI ALERT: Missing Report for {user['subject']}-{user["expected_date"]}"
    
    # Include subject and expected date in the prompt
    prompt = (
        f"URGENT: {user['user_name']} has not submitted the required report titled "
        f"'{user['subject']}' for {expected_date.strftime('%Y-%m-%d')}. "
        f"The report is now {delay_days} days overdue. Immediate action is needed! "
        f"Do not add any subject line. This email is from Rudra. "
        f"Regards, Max AI"
        f"Dont provide anything which is not needed at all"
    )

    body = await send_request_to_llm(prompt, user)
    await graph.send_mail(subject, body, user["email"])
    print(f"Alert email sent to {user['user_name']} at {user['email']} (Delay: {delay_days} days)")

async def send_request_to_llm(query_prompt, table_data):
    """Send a request to the LLM and return the response."""
    # Convert date objects to strings
    def serialize_dates(obj):
        if isinstance(obj, date):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")

    table_str = json.dumps(table_data, default=serialize_dates, indent=2)

    payload = {
        "inputs": {
            "query": query_prompt,
            "table": table_str,
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
            if "answer" in line_data:
                answers.append(line_data["answer"])
        except json.JSONDecodeError:
            print("Failed to decode line:", line)
    return " ".join(answers)

async def main():
    """Main function to check emails and send notifications."""
    print('Python Email Checker with AI Agent\n')
    while True:
        try:
            pending_emails = get_pending_emails()
            users_to_notify = await check_emails_for_subjects(graph, pending_emails)

            if users_to_notify:
                for user in users_to_notify:
                    if user["delay_days"] == 0:
                        await send_reminder(graph, user)
                    else:
                        await send_alert(graph, user)
            else:
                print(f"✅ All emails received on time for {get_current_date()}")

            await asyncio.sleep(30)  # Wait 24 hours before next check
        except Exception as e:
            print(f"An error occurred: {e}")
            time.sleep(10)

if __name__ == "__main__":
    # Set a specific date for testing (e.g., date(2023, 10, 26))
    TEST_DATE = None  # Set to None for production

    while True:
        try:
            asyncio.run(main())
        except Exception as e:
            print(f"Main process crashed: {e}, restarting...")
            time.sleep(10)