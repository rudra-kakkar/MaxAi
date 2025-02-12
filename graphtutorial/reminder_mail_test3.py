import asyncio
import configparser
from datetime import date, timedelta, datetime
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

def connect_db():
    return mysql.connector.connect(**db_config)

def get_today_emails():
    """Fetch expected emails from the database based on today's date."""
    today = date.today()
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT user_name, email, subject, expected_date, frequency FROM emails WHERE expected_date = %s", (today,))
    emails = cursor.fetchall()
    
    conn.close()
    return emails

def update_email_status(email, received_date=None, delay_days=None, status="Pending", frequency=None):
    """Update email status and delay in MySQL, and update the next expected date."""
    conn = connect_db()
    cursor = conn.cursor()
    
    if received_date:
        new_expected_date = received_date + timedelta(days=frequency) if frequency else received_date
        cursor.execute("UPDATE emails SET received_date = %s, delay_days = %s, status = %s, expected_date = %s WHERE email = %s",
               (received_date.strftime('%Y-%m-%d') if received_date else None, 
                delay_days, 
                status, 
                new_expected_date.strftime('%Y-%m-%d') if new_expected_date else None, 
                email))
    else:
        cursor.execute("UPDATE emails SET delay_days = delay_days + 1 WHERE email = %s", (email,))
    
    conn.commit()
    conn.close()

async def send_request_to_llm(query_prompt, table_data):
    """Send a request to the LLM and return the combined answers."""
    
    # Convert table_data (dictionary/list) into a formatted string
    if isinstance(table_data, dict):
        table_str = "\n".join([f"{k}: {v}" for k, v in table_data.items()])
    elif isinstance(table_data, list):
        table_str = "\n".join([", ".join(f"{k}: {v}" for k, v in row.items()) for row in table_data])
    else:
        table_str = str(table_data)  # Ensure it's always a string

    payload = {
        "inputs": {
            "query": query_prompt,
            "table": table_str,  # Ensure it's a string
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
                update_email_status(email)
                users_to_remind.append(user)
            else:
                update_email_status(email, received_date=users_who_sent_emails[email], delay_days=0, status="Received", frequency=user["frequency"])

        return users_to_remind
    else:
        print("No messages found in inbox.")
        for user in expected_emails:
            update_email_status(user["email"])
        return expected_emails

async def send_reminder_or_alert(graph: Graph, user):
    """Send either a reminder or an alert email based on the delay time."""
    if user.get("delay_days", 0) > 1:
        subject = f"ALERT: Missing Report for {user['user_name']}"
        prompt = f"URGENT: {user['user_name']} has not submitted the required report for more than a day. Immediate action needed!"
    else:
        subject = f"Reminder: Send Your Daily Report - {date.today()}"
        prompt = f"Dear {user['user_name']}, please send your required report as soon as possible."
    
    body = await send_request_to_llm(prompt, user)
    await graph.send_mail(subject, body, user["email"])
    print(f"Email sent to {user['user_name']} at {user['email']}")

async def main():
    """Main function to check emails and send notifications until received."""
    print('Python Email Checker with AI Agent\n')
    while True:
        try:
            check_date = date.today()
            today_expected_emails = get_today_emails()
            users_to_remind = await check_emails_for_subjects(graph, check_date, today_expected_emails)
            
            if users_to_remind:
                for user in users_to_remind:
                    await send_reminder_or_alert(graph, user)
            else:
                log_all_emails_received(check_date)  # Log if all emails are received

            await asyncio.sleep(30)  # Wait for a day before the next check
        except Exception as e:
            print(f"An error occurred: {e}")
            time.sleep(10)

def log_all_emails_received(check_date):
    """Log when all expected emails are received on time."""
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute("INSERT INTO emails (user_name, email, subject, expected_date, status) VALUES (%s, %s, %s, %s, %s)",
                   ("SYSTEM", "N/A", "All emails received on time", check_date, "Completed"))
    
    conn.commit()
    conn.close()
    print(f"Log entry added: All emails received on time for {check_date}")

if __name__ == "__main__":
    while True:
        try:
            asyncio.run(main())
        except Exception as e:
            print(f"Main process crashed: {e}, restarting...")
            time.sleep(10)
