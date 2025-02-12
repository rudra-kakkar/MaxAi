import pandas as pd
import requests
import json
import query  # First query module
import query1  # Second query module
import asyncio
# ------------------------------
# Section 1: Constants and Initialization
# ------------------------------

 # Initialize combined answers

# ------------------------------
# Section 2: Helper Functions
# ------------------------------

async def main():
    CSV_FILE_PATH = 'output_file1.csv'  # Path to the input CSV file
    API_URL = "http://app.knowmax.in/v1/completion-messages"
    HEADERS = {
        "Authorization": "Bearer app-Y6s7hruAKBs6VDrC3V9xE3wA",  # Replace with actual API key
        "Content-Type": "application/json"
    }
    full_answer = "" 
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

    # ------------------------------
    # Section 3: Data Preparation and Processing
    # ------------------------------

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
        print(location_answer)
        full_answer += location_answer + " "  # Accumulate answers

    # Step 2: Use the combined answer with the second query
    if full_answer.strip():  # Check if full_answer is not empty
        final_combined_answer = send_request_to_llm(query1.y, full_answer)
        print("Final Combined Answer:", final_combined_answer)

        import main
        graph=main.graph
        await main.send_mail(graph,auto=True,msg=final_combined_answer)
    else:
        print("No data processed in the first step.")


if __name__ == "__main__":
    asyncio.run(main())