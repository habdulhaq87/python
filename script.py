import os
import sys
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import textwrap
import ast
import json

# Function to parse string tuples (e.g., "(2103, 167)") into real tuple objects
def parse_tuple_string(tuple_string):
    try:
        return ast.literal_eval(tuple_string)
    except (ValueError, SyntaxError):
        print(f"Error parsing tuple string: {tuple_string}")
        return None

# Convert 'font_size' column to integers, handle missing or invalid values
def parse_font_size(font_size):
    try:
        return int(font_size)
    except (ValueError, TypeError):
        print(f"Error converting font size: {font_size}")
        return None  # Or you can set a default font size here

# Function to calculate the center of the rectangle and wrap the label text
def get_centered_position(x0, y0, x1, y1, label, font_size):
    center_x = (x0 + x1) // 2
    center_y = (y0 + y1) // 2

    # Approximate text dimensions (assuming average character width)
    average_char_width = font_size * 0.6  # Approximate average character width
    max_line_length = 20  # Maximum characters per line
    wrapped_text = textwrap.fill(label, width=max_line_length)

    lines = wrapped_text.split('\n')
    text_height = font_size * len(lines)
    text_width = max([len(line) for line in lines]) * average_char_width

    # Calculate the position to draw the text at the center of the rectangle
    text_x = center_x - text_width // 2
    text_y = center_y - text_height // 2

    return text_x, text_y, wrapped_text

def main():
    try:
        # Debug: Log start of the script
        print("Script started")

        # Authorize the service account for Google Sheets
        print("Loading Google Service Account credentials...")
        # Load credentials from environment variable
        service_account_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
        if not service_account_json:
            print("Error: The environment variable 'GOOGLE_SERVICE_ACCOUNT_JSON' is not set.")
            raise EnvironmentError("The environment variable 'GOOGLE_SERVICE_ACCOUNT_JSON' is not set.")
        
        service_account_info = json.loads(service_account_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            service_account_info,
            scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        )
        gc = gspread.authorize(creds)
        print("Google Service Account credentials loaded successfully.")

        # Fetch the data from Google Sheets using the service account
        print("Fetching data from Google Sheets...")
        sheet_url = "https://docs.google.com/spreadsheets/d/1EcEWYavEFsQIJkmr0VGgGiHbqXIrJKFIW_d3mM_teXc/edit?usp=sharing"
        spreadsheet = gc.open_by_url(sheet_url)
        position_sheet = spreadsheet.worksheet('position')
        position_data = position_sheet.get_all_records()
        print("Position data fetched successfully.")

        # Convert the data to a pandas DataFrame for easier processing
        df = pd.DataFrame(position_data)
        print("Position DataFrame loaded successfully. First 5 rows:")
        print(df.head())

        # Apply the function to each of the corner position columns
        for col in ['Corner Position 1', 'Corner Position 2', 'Corner Position 3', 'Corner Position 4']:
            df[col] = df[col].apply(parse_tuple_string)

        df['font_size'] = df['font_size'].apply(parse_font_size)

        # Debug: Ensure data was parsed correctly
        print("Data after parsing:")
        print(df.head())

        # Initialize SVG code
        svg_elements = []

        # Add a placeholder background (a plain white rectangle)
        svg_code = f'''<svg width="1000" height="1000" xmlns="http://www.w3.org/2000/svg">
          <rect width="1000" height="1000" style="fill:white;" />
        '''

        # Loop through the DataFrame and add each label to the SVG
        for index, row in df.iterrows():
            label = row['Label']
            corner1 = row['Corner Position 1']
            corner3 = row['Corner Position 3']
            font_size = row['font_size']

            # If font_size is not specified or invalid, set a default font size
            if not font_size:
                font_size = 40  # Default font size

            # Draw the rectangle outline
            if corner1 and corner3:
                x0 = min(corner1[0], corner3[0])
                y0 = min(corner1[1], corner3[1])
                x1 = max(corner1[0], corner3[0])
                y1 = max(corner1[1], corner3[1])

                width = x1 - x0
                height = y1 - y0

                # Add rectangle to SVG elements
                rect_element = f'<rect x="{x0}" y="{y0}" width="{width}" height="{height}" style="stroke:black; fill:none; stroke-width:2"/>'
                svg_elements.append(rect_element)

                # Get the centered position for the label
                text_x, text_y, wrapped_text = get_centered_position(x0, y0, x1, y1, label, font_size)

                # Add the label at the centered position
                # For multi-line text, need to add multiple <tspan> elements
                lines = wrapped_text.split('\n')
                text_element = f'<text x="{text_x}" y="{text_y + font_size}" font-size="{font_size}" fill="black">'
                dy = 0
                for line in lines:
                    text_element += f'<tspan x="{text_x}" dy="{dy}">{line}</tspan>'
                    dy = font_size  # Move down by font_size for next line
                text_element += '</text>'
                svg_elements.append(text_element)

        # Combine all SVG elements
        for element in svg_elements:
            svg_code += element + '\n'

        # Close the SVG tag
        svg_code += '</svg>'

        # Wrap the SVG code into an HTML template
        html_code = f'''<!DOCTYPE html>
        <html>
        <head>
            <title>Generated HTML</title>
        </head>
        <body>
            {svg_code}
        </body>
        </html>
        '''

        # Define the path where you want to save the HTML file
        output_directory = os.path.join(os.getcwd(), 'docs')
        os.makedirs(output_directory, exist_ok=True)
        output_html_path = os.path.join(output_directory, 'index.html')

        # Debug: Checking if directory is writable
        print(f"Checking write access for: {output_directory}")
        if os.access(output_directory, os.W_OK):
            print(f"Write access to {output_directory} confirmed.")
        else:
            print(f"WARNING: No write access to {output_directory}!")

        # Save the HTML code to the file
        try:
            print(f"Attempting to save HTML to {output_html_path}")
            with open(output_html_path, 'w') as html_file:
                html_file.write(html_code)
            print(f"New HTML file saved to {output_html_path}")
        except Exception as e:
            print(f"Error saving HTML file: {e}")
            raise

        # Create a .nojekyll file in the output directory
        nojekyll_path = os.path.join(output_directory, '.nojekyll')
        with open(nojekyll_path, 'w') as f:
            pass  # Just create an empty file

        print(f"Created .nojekyll in {output_directory}")

    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)  # Exit with an error code

if __name__ == '__main__':
    main()
