import os
import re
import sys
from collections import defaultdict

def extract_inline_styles_from_file(file_path):
    """Extract inline styles from an HTML file and return them as CSS classes"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all elements with style attributes
    style_pattern = r'(\w+(?:\s+\w+)*)\s+style="([^"]*)"'
    matches = re.findall(style_pattern, content)
    
    # Also find style attributes on any tag
    style_pattern2 = r'<([^>]+)\s+style="([^"]*)"[^>]*>'
    matches2 = re.findall(style_pattern2, content)
    
    all_matches = matches + matches2
    
    # Group similar styles
    style_groups = defaultdict(list)
    
    for match in all_matches:
        if len(match) == 2:
            element, style = match
        else:
            # Handle case where we have more groups
            element = match[0] if match[0] else match[1]
            style = match[1] if len(match) > 1 else match[2]
        
        # Normalize style string
        normalized_style = ';'.join(sorted(style.split(';')))
        if normalized_style.endswith(';'):
            normalized_style = normalized_style[:-1]
        
        style_groups[normalized_style].append((element, style))
    
    # Generate CSS classes
    css_classes = []
    replacements = {}
    
    class_counter = 1
    for style, instances in style_groups.items():
        if len(instances) > 1:  # Only create class if used more than once
            class_name = f"inline-style-{class_counter}"
            class_counter += 1
            css_classes.append(f".{class_name} {{ {style} }}")
            
            # Create replacement mapping
            for element, original_style in instances:
                replacements[f'{element} style="{original_style}"'] = f'{element} class="{class_name}"'
    
    return css_classes, replacements, content

def process_file(file_path):
    """Process a single HTML file to extract inline styles"""
    css_classes, replacements, content = extract_inline_styles_from_file(file_path)
    
    if not css_classes:
        return False
    
    # Apply replacements
    new_content = content
    for old, new in replacements.items():
        new_content = new_content.replace(old, new)
    
    # Add CSS classes to a shared stylesheet or create one
    css_dir = os.path.join(os.path.dirname(file_path), '..', 'static', 'css')
    os.makedirs(css_dir, exist_ok=True)
    
    # For simplicity, we'll add to a common inline-styles.css file
    css_file_path = os.path.join(css_dir, 'inline-styles.css')
    
    # Append to the file
    with open(css_file_path, 'a', encoding='utf-8') as f:
        f.write('\n/* Extracted from ' + os.path.relpath(file_path) + ' */\n')
        f.write('\n'.join(css_classes))
        f.write('\n')
    
    # Write back the modified HTML
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"Processed {file_path}: extracted {len(css_classes)} CSS classes")
    return True

def main():
    """Main function to process all HTML templates"""
    # Process base.html first
    process_file('templates/base.html')
    
    # Process all template files in templates directory
    for root, dirs, files in os.walk('templates'):
        for file in files:
            if file.endswith('.html'):
                process_file(os.path.join(root, file))
    
    # Process all template files in lands/templates/lands
    for root, dirs, files in os.walk('lands/templates/lands'):
        for file in files:
            if file.endswith('.html'):
                process_file(os.path.join(root, file))
    
    print("Done processing inline styles.")

if __name__ == "__main__":
    main()