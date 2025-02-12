import os
import pandas as pd
import requests
import json
import query  # First query module
import query1  # Second query module
import query3  #3rd query module
import query4  #4th query Module
import asyncio
import time

# ------------------------------
# Section 1: Constants and Initialization
# ------------------------------

API_URL = "http://app.knowmax.in/v1/completion-messages"
HEADERS = {
    "Authorization": "Bearer app-Y6s7hruAKBs6VDrC3V9xE3wA",  # Replace with actual API key
    "Content-Type": "application/json"
}
CSV_FILE_PATH = 'MaxicusReportInCSV.csv'  # Path to the input CSV file
CHECK_INTERVAL = 10  # Check every 10 seconds

# ------------------------------
# Section 2: Helper Functions
# ------------------------------

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
    return " ".join(answers)


def send_request_to_llm(query_prompt, table_data):
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


async def process_file():
    """Process the CSV file."""
    full_answer = ""

    # Load data and extract unique locations
    data = pd.read_csv(CSV_FILE_PATH)
    locations = data['Location'].dropna().unique()

    # Step 1: Process each location with the first query
    for location in locations:
        if "Total" in location:  # Skip "Total" rows
            continue
        filtered_data = data[(data['Location'] == location) | (data['Location'] == f"{location} Total")]
        csv_data = filtered_data.to_csv(index=False)

        # First LLM request
        location_answer = send_request_to_llm(query.x, csv_data)
        
        full_answer += location_answer + " "  # Accumulate answers

        # print(full_answer)
    # Step 2: Use the combined answer with the second query
    print("----------------------------------------------------------------------------------------------------------------------")
    print(full_answer.strip())
    if full_answer.strip():  # Check if full_answer is not empty
        First_combined_answer = send_request_to_llm(query1.y, full_answer)
        # print("yyyyyyyyyyyyyyy-------------------------------->",First_combined_answer)
        

        second_prompt_answer = send_request_to_llm(query3.a, full_answer)
        # print("aaaaaaaaaaaaaaaaa-------------------------------->",second_prompt_answer)

        Final_Answer = First_combined_answer +"\n--\n"+ second_prompt_answer
        print("Input of clean report")
        print(Final_Answer)
        Clean_report = send_request_to_llm(query4.cleaning, Final_Answer)

        print("----------------------------------------------Clean Report Sample\n",Clean_report)

        import main
        graph = main.graph
        await main.send_mail(graph, auto=True, msg=Final_Answer)
    else:
        print("No data processed in the first step.")


async def watch_file():
    """Periodically check for the file and process it if found."""
    while True:
        if os.path.exists(CSV_FILE_PATH):
            print(f"File {CSV_FILE_PATH} found. Processing...")
            await process_file()
            os.remove(CSV_FILE_PATH)  # Optional: Remove the file after processing
        else:
            print(f"File {CSV_FILE_PATH} not found. Checking again in {CHECK_INTERVAL} seconds.")
        await asyncio.sleep(CHECK_INTERVAL)


# ------------------------------
# Section 3: Main Execution
# ------------------------------

if __name__ == "__main__":
    asyncio.run(watch_file())
