import asyncio
import configparser
from msgraph.generated.models.o_data_errors.o_data_error import ODataError
from graph import Graph
import base64
import os
import time

# Load settings
config = configparser.ConfigParser()
config.read(['config.cfg', 'config.dev.cfg'])
azure_settings = config['azure']
graph = Graph(azure_settings)

# Keep track of the last processed message ID
last_processed_message_id = None

async def download_last_attachment(graph: Graph):
    global last_processed_message_id
    message_page = await graph.get_inbox()
    
    if message_page and message_page.value:
        latest_message = message_page.value[0]  # Get the most recent email
        if latest_message.id == last_processed_message_id:
            print("No new email to process.")
            return

        print(f"Processing email: {latest_message.subject}")
        last_processed_message_id = latest_message.id

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

async def main():
    print("Starting the email attachment downloader...")
    while True:
        try:
            await download_last_attachment(graph)
        except ODataError as odata_error:
            print("Error:")
            if odata_error.error:
                print(odata_error.error.code, odata_error.error.message)
        except Exception as e:
            print(f"An error occurred: {e}")
        
        print("Waiting for the next check...")
        time.sleep(1)  # Wait for 1 minute before checking again

if __name__ == "__main__":
    asyncio.run(main())
