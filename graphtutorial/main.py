# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

# <ProgramSnippet>
import asyncio
import configparser
from msgraph.generated.models.o_data_errors.o_data_error import ODataError
from graph import Graph
import base64
import os
from datetime import date

# graph=None
# Load settings
config = configparser.ConfigParser()
config.read(['config.cfg', 'config.dev.cfg'])
azure_settings = config['azure']
# global graph
graph = Graph(azure_settings)

async def main():
    print('Python Graph Tutorial\n')

    

    # await greet_user(graph)

    choice = -1

    while choice != 0:
        print('Please choose one of the following options:')
        print('0. Exit')
        print('1. Display access token')
        print('2. List my inbox')
        print('3. Send mail')
        print('4. Make a Graph call')
        print('5. Download latest file')
        try:
            choice = int(input())
        except ValueError:
            choice = -1

        try:
            if choice == 0:
                print('Goodbye...')
            elif choice == 1:
                await display_access_token(graph)
            elif choice == 2:
                await list_inbox(graph)
            elif choice == 3:
                await send_mail(graph)
            elif choice == 4:
                await make_graph_call(graph)
            elif choice == 5:
                await download_last_attachment(graph)
            else:
                print('Invalid choice!\n')
        except ODataError as odata_error:
            print('Error:')
            if odata_error.error:
                print(odata_error.error.code, odata_error.error.message)
# </ProgramSnippet>

# <GreetUserSnippet>
async def greet_user(graph: Graph):
    user = await graph.get_user()
    if user:
        print('Hello,', user.display_name)
        # For Work/school accounts, email is in mail property
        # Personal accounts, email is in userPrincipalName
        print('Email:', user.mail or user.user_principal_name, '\n')
# </GreetUserSnippet>
#<email to a specific user>

async def send_mail(graph: Graph,auto=False, msg=None):
    # Ask for subject, body, and recipient
    current_date = date.today()
    subject = f"MaxAi Report {current_date}"
    if not auto:
        body = input('Enter email body: ')
    recipient = "rudra.kakkar@kochiva.com"

    # Send the email
    if not auto:
        await graph.send_mail(subject, body, recipient)
    else:
        await graph.send_mail(subject, msg, recipient)

    print("Email sent to", recipient, "\n")
#</email to a specific user>

# <DisplayAccessTokenSnippet>
async def display_access_token(graph: Graph):
    token = await graph.get_user_token()
    print('User token:', token, '\n')
# </DisplayAccessTokenSnippet>

# <ListInboxSnippet>
async def list_inbox(graph: Graph):
    message_page = await graph.get_inbox()
    if message_page and message_page.value:
        # Output each message's details
        for message in message_page.value:
            print("Message id",message.id)
            print('Message:', message.subject)
            if (
                message.from_ and
                message.from_.email_address
            ):
                print('  From:', message.from_.email_address.name or 'NONE')
            else:
                print('  From: NONE')
            print('  Status:', 'Read' if message.is_read else 'Unread')
            print('  Received:', message.received_date_time)

        # If @odata.nextLink is present
        more_available = message_page.odata_next_link is not None
        print('\nMore messages available?', more_available, '\n')
# </ListInboxSnippet>

# # <SendMailSnippet>
# async def send_mail(graph: Graph):
#     # Send mail to the signed-in user
#     # Get the user for their email address
#     user = await graph.get_user()
#     if user:
#         user_email = user.mail or user.user_principal_name

#         await graph.send_mail('Testing Microsoft Graph', 'Hello world!', user_email or '')
#         print('Mail sent.\n')
# # </SendMailSnippet>

#<Download Last Email>
async def download_last_attachment(graph: Graph):
    message_page = await graph.get_inbox()
    if message_page and message_page.value:
        latest_message = message_page.value[0]  # Get the most recent email
        print(f"Downloading attachments from: {latest_message.subject}")

        attachments = await graph.get_attachments(latest_message.id)
        if attachments:
            for attachment in attachments:
                attachment_name = attachment['name']
                content = attachment['contentBytes']
                
                # Decode and save attachment
                decoded_content = base64.b64decode(content)
                save_path = os.path.join(os.getcwd(), attachment_name)
                with open(save_path, 'wb') as file:
                    file.write(decoded_content)
                
                print(f"Attachment '{attachment_name}' downloaded at: {save_path}")
        else:
            print("No attachments found in the latest email.")
    else:
        print("No messages found in inbox.")

#<end of last email download code>

# <MakeGraphCallSnippet>
async def make_graph_call(graph: Graph):
    await graph.make_graph_call()
# </MakeGraphCallSnippet>

# async def send_mail(graph: Graph):
#     # Ask for subject, body, and recipient
#     subject = input('Enter email subject: ')
#     body = input('Enter email body: ')
#     recipient = input('Enter recipient email address: ')

#     # Send the email
#     await graph.send_mail(subject, body, recipient)
#     print("Email sent.\n")


# Run main
if __name__=="__main__":
    asyncio.run(main())
