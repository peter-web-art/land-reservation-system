import os
import re
import sys

def process_template(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all style tags
    style_matches = re.findall(r'<style>.*?</style>', content, flags=re.DOTALL)
    
    if style_matches:
        # Get the directory and filename
        dir_name = os.path.dirname(file_path)
        file_name = os.path.basename(file_path)
        name_without_ext = os.path.splitext(file_name)[0]
        
        # Determine CSS directory based on template location
        if 'lands/templates/lands' in file_path:
            css_dir = os.path.join(dir_name, '..', '..', '..', 'static', 'css')
        else:
            css_dir = os.path.join(dir_name, '..', '..', 'static', 'css')
        
        # Create CSS directory if it doesn't exist
        os.makedirs(css_dir, exist_ok=True)
        
        # Save CSS to external file
        css_file_path = os.path.join(css_dir, f"{name_without_ext}.css")
        with open(css_file_path, 'w', encoding='utf-8') as css_file:
            # Extract just the CSS content (without <style> tags)
            css_content = style_matches[0][8:-9]  # Remove <style> and </style>
            css_file.write(css_content)
        
        # Replace style tag with link to external CSS
        replacement = '<link rel="stylesheet" href="{% static \"css/' + name_without_ext + '.css\" %}">'
        new_content = re.sub(r'<style>.*?</style>', replacement, content, flags=re.DOTALL)
        
        # Write back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"Processed {file_path}")

# Process base.html
process_template('templates/base.html')

# Process all template files in templates directory
for root, dirs, files in os.walk('templates'):
    for file in files:
        if file.endswith('.html'):
            process_template(os.path.join(root, file))

# Process all template files in lands/templates/lands
for root, dirs, files in os.walk('lands/templates/lands'):
    for file in files:
        if file.endswith('.html'):
            process_template(os.path.join(root, file))