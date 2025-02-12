import os
import time
import pandas as pd

def extract_columns_to_csv(input_excel, output_csv, columns_to_extract):
    """
    Extract specific columns from an Excel sheet and save them to a CSV file.

    Parameters:
    - input_excel: str, path to the input Excel file.
    - output_csv: str, path to the output CSV file.
    - columns_to_extract: list, names of the columns to extract.
    """
    try:
        # Read the Excel file
        df = pd.read_excel(input_excel)
        print("Columns in the Excel file:", df.columns)
        
        # Check if specified columns exist in the Excel file
        missing_columns = [col for col in columns_to_extract if col not in df.columns]
        if missing_columns:
            raise ValueError(f"The following columns are missing in the Excel file: {missing_columns}")
        
        # Extract the specified columns
        extracted_df = df[columns_to_extract]
        
        # Save the extracted columns to a CSV file
        extracted_df.to_csv(output_csv, index=False)
        print(f"Data successfully extracted to {output_csv}")
    
    except Exception as e:
        print(f"An error occurred: {e}")

# Parameters
input_excel = "./MaxicusReport.xlsx"  # Replace with your Excel file path
output_csv = "MaxicusReportInCSV.csv"  # Replace with your desired CSV file path
columns_to_extract = [
    "Location", "Process Name", "Client", "Revenue Opportunity", 
    "RO W-1", "RO W-2", "RO W-3", "Rev Ach W-1", 
    "Rev Ach W-2", "Rev Ach W-3", "Rev Loss W-1", 
    "Rev Loss W-2", "Rev Loss W-3", "Rev Loss Overall"
]

# Continuous monitoring loop
print("Monitoring for the file...")
while True:
    if os.path.exists(input_excel):  # Check if the file exists
        print(f"File {input_excel} found. Processing...")
        extract_columns_to_csv(input_excel, output_csv, columns_to_extract)
        os.remove(input_excel)  # Remove the file after processing if needed
        print(f"File {input_excel} processed and removed.")
    else:
        print(f"File {input_excel} not found. Waiting...")
    time.sleep(10)  # Wait for 10 seconds before checking again
