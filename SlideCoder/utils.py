import cv2
import numpy as np
from PIL import Image
import base64
import os


def encode_image(image_path):
    """Convert image file to base64 string"""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"Error encoding image: {str(e)}")
        raise


def load_image_file(image_path):
    """Load image file directly"""
    try:
        return Image.open(image_path)
    except Exception as e:
        print(f"Error loading image: {str(e)}")
        raise


def cleanup_response(response):
    """Clean up the code response from AI models"""
    lines = response.strip().split('\n')
    cleaned_lines = []
    in_code_block = False

    # Identify and extract the first complete code block
    for line in lines:
        stripped = line.strip()

        # Detect code block start
        if stripped.startswith('```python'):
            in_code_block = True
            continue 
        # Detecting the end of a code block
        if in_code_block and stripped.startswith('```'):
            break

        if in_code_block:
            cleaned_lines.append(line)

    if not cleaned_lines:
        return original_cleanup_logic(response)

    while cleaned_lines and not cleaned_lines[0].strip():
        cleaned_lines.pop(0)
    while cleaned_lines and not cleaned_lines[-1].strip():
        cleaned_lines.pop()

    # Format standardization
    cleaned_code = '\n'.join(cleaned_lines)
    return cleaned_code.replace('\r', '') \
        .replace('\t', '    ') \
        .rstrip('`') 

def original_cleanup_logic(response):
    """Clean up the code response from AI models"""
    lines = response.strip().split('\n')
    start_idx = 0
    end_idx = len(lines)

    for i, line in enumerate(lines):
        if 'prs.save(' in line or 'presentation.save(' in line:
            # Find the corresponding except block
            for j in range(i, len(lines)):
                if lines[j].strip().startswith('except '):
                    except_indent = len(lines[j]) - len(lines[j].lstrip())
                    k = j + 1
                    while k < len(lines):
                        current_line = lines[k]
                        current_indent = len(current_line) - len(current_line.lstrip())
                        if current_line.strip() and current_indent <= except_indent:
                            break
                        k += 1
                    end_idx = k
                    break
            break

    code_lines = lines[start_idx:end_idx]

    while code_lines and not code_lines[0].strip():
        code_lines.pop(0)
    while code_lines and not code_lines[-1].strip():
        code_lines.pop()

    cleaned_code = '\n'.join(code_lines)
    cleaned_code = cleaned_code.replace('\r', '') \
        .replace('\t', '    ') \
        .rstrip('`')

    return cleaned_code


def modify_save_path(code, code_path):
    """Modify the save path in the generated code to match the code filename"""
    if 'prs.save(' in code:
        # Extract the filename from the original save command
        start = code.find('prs.save(')
        end = code.find(')', start)
        original_save = code[start:end+1]
        
        # Get the base filename without extension
        ppt_filename = os.path.splitext(os.path.basename(code_path))[0] + '.pptx'
        # Replace with new save path
        new_save = f'prs.save("./generated_ppts/{ppt_filename}")'
        code = code.replace(original_save, new_save)
    
    return code


def get_description(image_path):
    image = cv2.imread(image_path)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    lower_red = np.array([0, 100, 100])
    upper_red = np.array([10, 255, 255])
    mask1 = cv2.inRange(hsv, lower_red, upper_red)

    lower_red = np.array([160, 100, 100])
    upper_red = np.array([179, 255, 255])
    mask2 = cv2.inRange(hsv, lower_red, upper_red)

    mask = cv2.bitwise_or(mask1, mask2)
    edges = cv2.Canny(mask, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Format the description text
    description = "Layout Description:\n"
    
    for i, contour in enumerate(contours, 1):
        x, y, w, h = cv2.boundingRect(contour)
        if w > 50 and h > 50:  # Filter out small contours
            description += f"\nBlock {i}:\n"
            description += f"Position: ({x}, {y})\n"
            description += f"Size: {w}x{h} pixels\n"
            
            # Add relative position information
            rel_x = x / image.shape[1]  # relative to image width
            rel_y = y / image.shape[0]  # relative to image height
            rel_w = w / image.shape[1]
            rel_h = h / image.shape[0]
            description += f"Relative position: {rel_x:.2f}x{rel_y:.2f}\n"
            description += f"Relative size: {rel_w:.2f}x{rel_h:.2f}\n"

    return description

