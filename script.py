# Import required libraries
from PIL import Image
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import textwrap
import ast
import math
import os
import json

# Function to parse string tuples (e.g., "(2103, 167)") into real tuple objects
def parse_tuple_string(tuple_string):
    try:
        return ast.literal_eval(tuple_string)
    except (ValueError, SyntaxError):
        return None

# Convert 'font_size' column to integers, handle missing or invalid values
def parse_font_size(font_size):
    try:
        return int(font_size)
    except (ValueError, TypeError):
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

# Function to generate offsets to prevent overlap
def generate_offsets(num_points, radius):
    offsets = []
    for i in range(num_points):
        angle = 2 * math.pi * i / num_points
        offset_x = radius * 2 * math.cos(angle)
        offset_y = radius * 2 * math.sin(angle)
        offsets.append((offset_x, offset_y))
    return offsets

def main():
    # Authorize the service account for Google Sheets
    # Load credentials from environment variable
    service_account_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
    if not service_account_json:
        raise EnvironmentError("The environment variable 'GOOGLE_SERVICE_ACCOUNT_JSON' is not set.")
    service_account_info = json.loads(service_account_json)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        service_account_info,
        scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    )
    gc = gspread.authorize(creds)

    # Fetch the data from Google Sheets using the service account
    sheet_url = "https://docs.google.com/spreadsheets/d/1EcEWYavEFsQIJkmr0VGgGiHbqXIrJKFIW_d3mM_teXc/edit?usp=sharing"
    spreadsheet = gc.open_by_url(sheet_url)
    position_sheet = spreadsheet.worksheet('position')
    position_data = position_sheet.get_all_records()

    # Convert the data to a pandas DataFrame for easier processing
    df = pd.DataFrame(position_data)

    # Apply the function to each of the corner position columns
    for col in ['Corner Position 1', 'Corner Position 2', 'Corner Position 3', 'Corner Position 4']:
        df[col] = df[col].apply(parse_tuple_string)

    df['font_size'] = df['font_size'].apply(parse_font_size)

    # Load the background image from the local repository
    background_image_path = 'background.jpg'  # Ensure this image is in the repository
    img = Image.open(background_image_path)

    # Save the image to a file in the output directory
    output_directory = 'docs'  # Save outputs in the 'docs' directory for GitHub Pages
    os.makedirs(output_directory, exist_ok=True)
    output_image_filename = 'output_image.png'
    output_image_path = os.path.join(output_directory, output_image_filename)

    # Save the image
    img.save(output_image_path, format='PNG')

    # Get image dimensions
    img_width, img_height = img.size

    # Initialize SVG code
    svg_elements = []

    # Add the image as the background
    svg_code = f'''<svg width="{img_width}" height="{img_height}" xmlns="http://www.w3.org/2000/svg">
      <image href="{output_image_filename}" x="0" y="0" width="{img_width}" height="{img_height}"/>
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

    # ------------------- Circle Drawing Code -------------------

    # Now, fetch the points data from the 'points' worksheet
    points_sheet = spreadsheet.worksheet('points')
    points_data = points_sheet.get_all_records()

    # Convert the points data to a DataFrame
    points_df = pd.DataFrame(points_data)

    # Parse the 'Position' column to get the coordinates
    points_df['Position'] = points_df['Position'].apply(parse_tuple_string)

    # Fetch 'Profiles' worksheet data
    profiles_sheet = spreadsheet.worksheet('Profiles')
    profiles_data = profiles_sheet.get_all_records()

    # Convert to DataFrame
    profiles_df = pd.DataFrame(profiles_data)

    # Build a mapping from Profile to color and name
    profiles_mapping = {}
    profiles_list = []
    for index, row in profiles_df.iterrows():
        profile = row['Profile']
        color_hex = row['Color']
        name = row['Name']
        # Convert hex color to RGB tuple
        color_rgb = tuple(int(color_hex.strip('#')[i:i+2], 16) for i in (0, 2, 4))
        color_rgb_str = f'rgb{color_rgb}'
        profiles_mapping[profile] = {
            'color': color_rgb_str,
            'name': name
        }
        profiles_list.append(profile)

    # Circle properties
    circle_radius = 10  # Adjust the circle size as needed

    # Generate offsets dynamically around the circle to prevent overlap
    offsets_list = generate_offsets(len(profiles_list), circle_radius)
    # Build offsets dict
    offsets = {}
    for profile, offset in zip(profiles_list, offsets_list):
        offsets[profile] = offset

    # Now, draw the circles for each point based on the profiles
    for index, row in points_df.iterrows():
        position = row['Position']
        if position:
            x, y = position
            # For each profile, check if the value is 1
            for profile in profiles_list:
                value = row.get(profile, 0)
                if value == 1:
                    profile_info = profiles_mapping.get(profile)
                    if profile_info:
                        color_rgb_str = profile_info['color']
                        name = profile_info['name']
                        offset_x, offset_y = offsets.get(profile, (0, 0))
                        x_adj = x + offset_x
                        y_adj = y + offset_y

                        # Add circle to SVG elements
                        circle_element = f'<circle cx="{x_adj}" cy="{y_adj}" r="{circle_radius}" fill="{color_rgb_str}" stroke="{color_rgb_str}"/>'
                        svg_elements.append(circle_element)

                        # Add the profile name next to the circle
                        label_font_size = 20  # Adjust as needed

                        # Position the text to the right of the circle
                        text_x = x_adj + circle_radius + 5  # Slightly offset to the right
                        text_y = y_adj + label_font_size / 2  # Adjust vertically

                        # Add text element
                        text_element = f'<text x="{text_x}" y="{text_y}" font-size="{label_font_size}" fill="black">{name}</text>'
                        svg_elements.append(text_element)

    # ------------------- End of Circle Drawing Code -------------------

    # Combine all SVG elements
    for element in svg_elements:
        svg_code += element + '\n'

    # Close the SVG tag
    svg_code += '</svg>'

    # Wrap the SVG code into an HTML template
    html_code = f'''<!DOCTYPE html>
    <html>
    <head>
        <title>Output Image</title>
    </head>
    <body>
        {svg_code}
    </body>
    </html>
    '''

    # Define the path where you want to save the HTML file
    output_html_path = os.path.join(output_directory, 'index.html')  # Renamed to index.html

    # Save the HTML code to the file
    with open(output_html_path, 'w') as html_file:
        html_file.write(html_code)

    print(f"New HTML file saved to {output_html_path}")

    # Create a .nojekyll file in the output directory
    nojekyll_path = os.path.join(output_directory, '.nojekyll')
    with open(nojekyll_path, 'w') as f:
        pass  # Just create an empty file

    print(f"Created .nojekyll in {output_directory}")

if __name__ == '__main__':
    main()
