import requests
import pandas as pd
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import graphtutorial.query as query

# Load the CSV file
csv_file_path = 'output_file1.csv'
data1 = pd.read_csv(csv_file_path)

# Convert the DataFrame to a CSV string
csv_data = data1.to_csv(index=False)

url = "http://app.knowmax.in/v1/completion-messages"
headers = {
    "Authorization": "Bearer app-Y6s7hruAKBs6VDrC3V9xE3wA",  # Replace with your actual API key
    "Content-Type": "application/json"
}

# Prepare the payload
data = {
    "inputs": {
        "query": query.x,  # Replace with your query logic
        "table": csv_data,          # Pass the CSV data as a string
        "table2": csv_data          # Example of passing it multiple times
    },
    "response_mode": "streaming",
    "user": "abc-123"
}

# Send the POST request
response = requests.post(url, headers=headers, json=data)

# Print the response
print("Status Code:", response.status_code)

# Process the response text to extract answers
if response.status_code == 200:
    answers = []
    for line in response.text.splitlines():
        # Strip the "data: " prefix from each line before parsing as JSON
        line = line.lstrip("data: ").strip()

        # Skip empty lines
        if not line:
            continue
        
        try:
            # Parse the cleaned line as JSON
            line_data = json.loads(line)
            # Extract the "answer" field if it exists
            answer = line_data.get("answer")
            if answer:
                answers.append(answer)
        except json.JSONDecodeError:
            print("Failed to decode line:", line)

    # Combine all answers into a single string
    full_answer = " ".join(answers)
    print("Full Answer:", full_answer)
else:
    print("Failed to retrieve data. Response Text:", response.text)

# Email details
sender_email = "merudrakakkar1@gmail.com"  # Replace with your email
receiver_email = "merudrakakkar@gmail.com"  # Replace with the recipient's email
subject = "API Response Answer"
body = "Here is the answer from the API:\n\n" + full_answer  # full_answer is the combined answer from previous steps

# SMTP server details
smtp_server = "smtp.gmail.com"
smtp_port = 587  # Use 465 for SSL, 587 for TLS

# Login credentials for your email account
email_password = "rudra@123"  # Replace with your email password (use App Passwords for Gmail if 2FA is enabled)

# Create the email message
msg = MIMEMultipart()
msg['From'] = sender_email
msg['To'] = receiver_email
msg['Subject'] = subject

# Attach the body with the email
msg.attach(MIMEText(body, 'plain'))

# Connect to the SMTP server and send the email
try:
    # Set up the server
    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()  # Secure the connection using TLS

    # Log in to the email account
    server.login(sender_email, email_password)

    # Send the email
    text = msg.as_string()
    server.sendmail(sender_email, receiver_email, text)
    print("Email sent successfully!")

except Exception as e:
    print(f"Failed to send email: {e}")

finally:
    server.quit()
