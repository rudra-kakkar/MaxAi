import asyncio

async def check_and_notify_multiple(graph, senders, auto_reply_subject, auto_reply_body_template):
    """
    Check if emails have been received from multiple senders.
    If not, send an automated email to each sender.

    :param graph: Graph instance to interact with Microsoft Graph API
    :param senders: List of sender email addresses to check
    :param auto_reply_subject: Subject of the automated email
    :param auto_reply_body_template: Template for the automated email body
    """
    message_page = await graph.get_inbox()
    received_senders = set()

    if message_page and message_page.value:
        # Collect all senders from the inbox
        for message in message_page.value:
            if message.from_ and message.from_.email_address:
                received_senders.add(message.from_.email_address.address.lower())

    # Check each sender in the provided list
    for sender_email in senders:
        if sender_email.lower() not in received_senders:
            print(f"No email received from {sender_email}. Sending automated reply...")
            auto_reply_body = auto_reply_body_template.format(sender_email=sender_email)
            await send_automated_email(graph, sender_email, auto_reply_subject, auto_reply_body)
        else:
            print(f"Email from {sender_email} already received.")

async def send_automated_email(graph, recipient_email, subject, body):
    """
    Send an automated email.

    :param graph: Graph instance to interact with Microsoft Graph API
    :param recipient_email: The email address of the recipient
    :param subject: Subject of the email
    :param body: Body of the email
    """
    email_message = {
        "message": {
            "subject": subject,
            "body": {
                "contentType": "Text",
                "content": body
            },
            "toRecipients": [
                {
                    "emailAddress": {
                        "address": recipient_email
                    }
                }
            ]
        }
    }
    response = await graph.send_mail(email_message)
    if response:
        print(f"Automated email sent to {recipient_email}")
    else:
        print(f"Failed to send automated email to {recipient_email}")

# Example usage
async def main():
    from graph import Graph  # Replace with your actual Graph client import

    graph = Graph()  # Initialize your Microsoft Graph API client
    senders = [
        "person1@domain.com",
        "person2@domain.com",
        "person3@domain.com"
    ]  # List of senders' email addresses to check
    auto_reply_subject = "Follow-up: Email Not Received"
    auto_reply_body_template = (
        "Hello {sender_email},\n\n"
        "We noticed we haven't received an email from you. Please let us know if there's anything we can assist with.\n\n"
        "Best regards,\nYour Team"
    )

    await check_and_notify_multiple(graph, senders, auto_reply_subject, auto_reply_body_template)

# Run the main function
asyncio.run(main())
