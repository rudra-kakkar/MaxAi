import pandas as pd
import requests
import json
import graphtutorial.query as query


# Load the CSV file
csv_file_path = 'output_file1.csv'
data1 = pd.read_csv(csv_file_path)

# Extract unique locations (excluding NaN entries)
locations = data1['Location'].dropna().unique()

# API details
url = "http://app.knowmax.in/v1/completion-messages"
headers = {
    "Authorization": "Bearer app-Y6s7hruAKBs6VDrC3V9xE3wA",  # Replace with your actual API key
    "Content-Type": "application/json"
}

# Iterate over each location and send data including "Total" row for each
for location in locations:
    # Skip rows where the location contains "Total"
    if "Total" in location:
        continue
    
    # Filter rows for the current location and its "Total" row
    location_data = data1[(data1['Location'] == location) | ((data1['Location'] == f"{location} Total"))]
    
    # Convert the filtered DataFrame to CSV format
    csv_data = location_data.to_csv(index=False)
    
    # Prepare the payload
    # print(csv_data)
    data = {
        "inputs": {
            "query": query.x,  # Use location as query
            "table": csv_data,  # Pass the location-specific and Total row CSV data
        },
        "response_mode": "streaming",
        "user": "abc-123"
    }
    
    # Send the POST request
    response = requests.post(url, json=data, headers=headers)
    
    # Handle the response
    if response.status_code == 200:
        print(f"Data for location '{location}' sent successfully.")
    else:
        print(f"Failed to send data for location '{location}'. Status code: {response.status_code}, Error: {response.text}")

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

