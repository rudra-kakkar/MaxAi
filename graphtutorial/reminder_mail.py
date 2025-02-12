import asyncio
import configparser
from msgraph.generated.models.o_data_errors.o_data_error import ODataError
from graph import Graph
from datetime import date, timedelta
import requests
import json

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

# Initialize OpenAI client

# List of users who are supposed to send emails
USERS = [
    {"name": "Rudra", "email": "rudra.kakkar@kochiva.com"},
    {"name": "corp", "email": "corp@kochartech.com"},
#     {"name": "Akshit", "email": "akshit.soni@kochiva.com"},
#     {"name": "Subhash", "email": "subhash.kochhar@kochiva.com"}
# ]]
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
        line = line.lstrip("data: ").strip()  # Remove prefix and trim
        if not line:
            continue
        try:
            line_data = json.loads(line)
            answer = line_data.get("answer")
            if answer:
                answers.append(answer)
        except json.JSONDecodeError:
            print("Failed to decode line:", line)
    print(answers)
    return " ".join(answers)




async def check_emails_from_users(graph: Graph):
    """
    Check the inbox for emails from the specified users.
    Returns a list of users who haven't sent an email.
    """
    current_date = date.today()
    last_expected_date = current_date - timedelta(days=1)  # Emails should be sent daily

    # Fetch the inbox
    message_page = await graph.get_inbox()
    if message_page and message_page.value:
        # Create a set of users who have sent emails
        users_who_sent_emails = set()

        for message in message_page.value:
            if (
                message.from_ and
                message.from_.email_address and
                message.received_date_time.date() >= last_expected_date
            ):
                users_who_sent_emails.add(message.from_.email_address.address.lower())

        # Check which users haven't sent emails
        users_to_remind = [
            user for user in USERS if user["email"].lower() not in users_who_sent_emails
        ]

        return users_to_remind
    else:
        print("No messages found in inbox.")
        return []

# async def generate_reminder_message(user):
#     """
#     Generate a personalized reminder message using OpenAI's GPT.
#     """
#     prompt = f"Write a polite and professional reminder email to {user['name']} to send their daily report."
#     response = openai_client.chat.completions.create(
#         model="gpt-4",  # Use GPT-4 or GPT-3.5
#         messages=[
#             {"role": "system", "content": "You are a helpful assistant."},
#             {"role": "user", "content": prompt}
#         ]
#     )
#     return response.choices[0].message.content

async def send_reminder(graph: Graph, user):
    """
    Send a reminder email to a user who hasn't sent their report.
    """
    print(user)
    prompt = f"Write a professional mail regarding you have not send the report for today. Please check table for more details"
    print("Prompt",prompt )
    current_date = date.today()
    subject = f"Reminder: Send Your Daily Report - {current_date}"
    x = f"User name {user["name"]}, Current date: {current_date} sender: Rudra kakkar "
    body = await send_request_to_llm(prompt,x)  # AI-generated message

    await graph.send_mail(subject, body, user["email"])
    print(f"Reminder sent to {user['name']} at {user['email']}")

async def main():
    """
    Main function to check for emails and send reminders.
    """
    print('Python Email Checker with AI Agent\n')

    # Check for emails from users
    users_to_remind = await check_emails_from_users(graph)

    if users_to_remind:
        print("Sending reminders to the following users:")
        for user in users_to_remind:
            print(f"- {user['name']} ({user['email']})")
            await send_reminder(graph, user)
    else:
        print("All users have sent their emails. No reminders needed.")

# Run main
if __name__ == "__main__":
    asyncio.run(main())