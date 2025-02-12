import asyncio
import mysql.connector
from datetime import datetime
from collections import defaultdict
import configparser
from graph import Graph


# Assuming the Graph class and other necessary imports are already defined as in your provided code

# Load settings
config = configparser.ConfigParser()
config.read(['config.cfg', 'config.dev.cfg'])
azure_settings = config['azure']
graph = Graph(azure_settings)

# Define the email addresses for L1, L2, L3, and L4
L1_EMAIL = "rudra.kakkar@kochiva.com"
L2_EMAIL = "rudra.kakkar@kochiva.com"
L3_EMAIL = "rudra.kakkar@kochiva.com"
L4_EMAIL = "rudra.kakkar@kochiva.com"

# MySQL database connection setup
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="myuser",
        password="mypassword",
        database="mails"
    )

# Function to check if delays happen more than 2 times in a month
def is_frequent_delay(email, delay_data):
    monthly_delays = defaultdict(int)
    for delay in delay_data:
        if delay['email'] == email:
            delay_date = datetime.strptime(delay['created_at'], "%Y-%m-%d %H:%M:%S")
            month_key = delay_date.strftime("%Y-%m")
            monthly_delays[month_key] += 1
            if monthly_delays[month_key] > 2:
                return True
    return False

async def send_delay_emails(graph, delay_data):
    for delay in delay_data:
        email = delay['email']
        subject = delay['subject']
        delay_days = delay['delay_days']
        created_at = delay['created_at']

        # Determine the recipient based on delay days
        if delay_days >= 7:
            recipient = L3_EMAIL
            cc_recipients = [L2_EMAIL, L1_EMAIL]
        elif delay_days >= 5:
            recipient = L2_EMAIL
            cc_recipients = [L1_EMAIL]
        elif delay_days >= 3:
            recipient = L1_EMAIL
            cc_recipients = []
        else:
            continue

        # Prepare the email body
        body = f"Subject: {email}\nDelay Days: {delay_days}\nCreated At: {created_at}\n\nThis email is sent due to a delay in the expected delivery."

        # Modify the send_mail function to support cc_recipients (if you wish to do so in the future)
        if cc_recipients:
            # Handle cc_recipients if needed
            cc_emails = ', '.join(cc_recipients)
            body += f"\nCC: {cc_emails}"

        # Send the email to the main recipient
        try:
            await graph.send_mail(subject, body, recipient)  # Your `send_mail` accepts these params
            print(f"Email sent to {recipient} with CC to {', '.join(cc_recipients) if cc_recipients else 'no one'}")
        except Exception as e:
            print(f"Error sending email to {recipient}: {e}")

    # Check for frequent delays and notify L4
    frequent_delay_emails = set()
    for delay in delay_data:
        if is_frequent_delay(delay['email'], delay_data):
            frequent_delay_emails.add(delay['email'])

    for email in frequent_delay_emails:
        subject = "Frequent Delays Notification"
        body = f"The email address {email} has experienced frequent delays more than 2 times in a month."
        try:
            await graph.send_mail(subject, body, L4_EMAIL)  # Sending notification email to L4
            print(f"Notification sent to {L4_EMAIL} about frequent delays for {email}")
        except Exception as e:
            print(f"Error sending notification to {L4_EMAIL}: {e}")

# Function to fetch delay data from MySQL
def fetch_delay_data():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Query to fetch delay data
    query = """
    SELECT delay_id, email, subject, expected_date, delay_days, escalated, created_at
    FROM email_delays
    """
    cursor.execute(query)
    delay_data = cursor.fetchall()

    cursor.close()
    connection.close()
    
    return delay_data

async def main():
    print('Python Graph Tutorial\n')
    # Assuming graph is already initialized as in your provided code
    
    # Fetch delay data from MySQL
    delay_data = fetch_delay_data()
    
    # Call the function to send delay emails
    await send_delay_emails(graph, delay_data)

# Run main
if __name__ == "__main__":
    asyncio.run(main())
