import cv2
import numpy as np
import argparse
import os
import json
import shutil
from datetime import datetime

import tqdm

def calculate_complexity(block):
    """Calculate the complexity of the image block and use the average value of the gradient magnitude as the complexity indicator"""
    gray = cv2.cvtColor(block, cv2.COLOR_BGR2GRAY) if len(block.shape) == 3 else block
    gradient_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    gradient_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    gradient_magnitude = np.sqrt(gradient_x**2 + gradient_y**2)
    return np.mean(gradient_magnitude)

def process_image(image_path, output_dir, grid_size=8, complexity_threshold=None, surrounding_threshold=0.98, draw=None, depth=1, min_box_size=0):
    """Processing images: dividing grids and marking complex areas"""
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Unable to load image: {image_path}")
    
    height, width = img.shape[:2]
    block_height = height / grid_size
    block_width = width / grid_size
    
    result = img.copy()
    
    complexity_matrix = calculate_complexity_matrix(img, grid_size, complexity_threshold)
    
    result, boxes_info = recursive_process_regions(img, result, complexity_matrix, block_height, block_width, grid_size, surrounding_threshold, draw, 1, depth, min_box_size)
    
    img_name = os.path.splitext(os.path.basename(image_path))[0]
    img_output_dir = os.path.join(output_dir, img_name)
    os.makedirs(img_output_dir, exist_ok=True)
    
    original_img_path = os.path.join(img_output_dir, f"{img_name}_original.png")
    shutil.copy2(image_path, original_img_path)
    
    annotated_img_path = os.path.join(img_output_dir, f"{img_name}_annotated.png")
    cv2.imwrite(annotated_img_path, result)
    
    img_details = {
        "parameters": {
            "grid_size": grid_size,
            "complexity_threshold": complexity_threshold,
            "surrounding_threshold": surrounding_threshold,
            "depth": depth,
            "min_box_size": min_box_size,
            "timestamp": datetime.now().isoformat()
        },
        "original_path": image_path,
        "copied_original_path": original_img_path,
        "annotated_path": annotated_img_path,
        "image_size": {"width": width, "height": height},
        "boxes": []
    }
    
    for i, box in enumerate(boxes_info):
        box_id = i + 1
        top, bottom, left, right = box["position"]
        box_img = img[top:bottom, left:right]
        box_img_path = os.path.join(img_output_dir, f"{img_name}_box{box_id}.png")
        cv2.imwrite(box_img_path, box_img)
        box["id"] = box_id
        box["cropped_path"] = box_img_path
        box["size"] = {"width": right - left, "height": bottom - top}
        img_details["boxes"].append(box)
    
    json_path = os.path.join(img_output_dir, f"{img_name}_info.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(img_details, f, ensure_ascii=False, indent=2)
    
    return result, img_output_dir

def calculate_complexity_matrix(img, grid_size, complexity_threshold=None):
    """Calculate the complexity matrix of an image"""
    height, width = img.shape[:2]
    block_height = height / grid_size
    block_width = width / grid_size
    
    complexities = []
    
    for i in range(grid_size):
        for j in range(grid_size):
            y_start = int(i * block_height)
            y_end = int((i + 1) * block_height) if i < grid_size - 1 else height
            x_start = int(j * block_width)
            x_end = int((j + 1) * block_width) if j < grid_size - 1 else width
            
            block = img[y_start:y_end, x_start:x_end]
            complexity = calculate_complexity(block)
            complexities.append((complexity, (i, j)))
    
    complexity_values = [c for c, _ in complexities]
    threshold = np.median(complexity_values) * 1.5 if complexity_threshold is None else complexity_threshold
    
    complexity_matrix = np.zeros((grid_size, grid_size), dtype=bool)
    
    for complexity, (i, j) in complexities:
        if complexity > threshold:
            complexity_matrix[i, j] = True
    
    return complexity_matrix

def recursive_process_regions(original_img, current_img, complexity_matrix, block_height, block_width, grid_size, surrounding_threshold, draw, current_depth, max_depth, min_box_size=0):
    """Recursively process connected regions of different depths"""
    height, width = original_img.shape[:2]
    result = current_img.copy()
    all_boxes = []
    
    # Find the area surrounded by the green block
    surrounded_matrix = find_surrounded_blocks(complexity_matrix, surrounding_threshold)
    
    # Merge the complex area and the enclosed area to form the final green area mark
    green_matrix = complexity_matrix | surrounded_matrix
    
    # Find the connected area at the current depth
    regions = find_connected_regions(green_matrix)
    
    # Draw the connected region boundary at the current depth
    for region in regions:
        if not region:
            continue
        
        # Find the minimum enclosing rectangle of a connected region
        min_i = min(i for i, _ in region)
        max_i = max(i for i, _ in region)
        min_j = min(j for _, j in region)
        max_j = max(j for _, j in region)
        
        # Calculation area size (number of grids)
        region_size = (max_i - min_i + 1) * (max_j - min_j + 1)
        
        # If the region is smaller than the minimum allowed size, skip
        if min_box_size > 0 and region_size < min_box_size:
            continue
        
        top = int(min_i * block_height)
        bottom = int((max_i + 1) * block_height) if max_i < grid_size - 1 else height
        left = int(min_j * block_width)
        right = int((max_j + 1) * block_width) if max_j < grid_size - 1 else width
        
        cv2.rectangle(result, (left, top), (right, bottom),(255, 234, 0), 5)
        
        box_info = {
            "depth": current_depth,
            "position": [top, bottom, left, right],
            "grid_coordinates": {
                "min_i": min_i,
                "max_i": max_i,
                "min_j": min_j,
                "max_j": max_j
            },
            "grid_size": region_size
        }
        all_boxes.append(box_info)
    
    # If the maximum depth has been reached, return the result
    if current_depth >= max_depth:
        return result, all_boxes
    
    # Processing the connected area at the next depth
    for region in regions:
        if not region:
            continue
        
        # Find the minimum enclosing rectangle of a connected region
        min_i = min(i for i, _ in region)
        max_i = max(i for i, _ in region)
        min_j = min(j for _, j in region)
        max_j = max(j for _, j in region)
        
        region_size = (max_i - min_i + 1) * (max_j - min_j + 1)
        
        if min_box_size > 0 and region_size < min_box_size:
            continue
    
        region_mask = np.zeros((grid_size, grid_size), dtype=bool)
        for i, j in region:
            region_mask[i, j] = True
        region_mask = region_mask ^ complexity_matrix
        region_mask = find_surrounded_blocks(region_mask, surrounding_threshold)
        inner_mask = region_mask
        # Create the complexity matrix for the interior region (using a subset of the original complexity matrix)
        inner_complexity = np.zeros((grid_size, grid_size), dtype=bool)
        for i in range(grid_size):
            for j in range(grid_size):
                if inner_mask[i, j]:
                    inner_complexity[i, j] = complexity_matrix[i, j]
        
        # Recursively process inner regions
        result, inner_boxes = recursive_process_regions(original_img, result, inner_complexity, 
                                          block_height, block_width, grid_size, 
                                          surrounding_threshold, draw, 
                                          current_depth + 1, max_depth, min_box_size)
        
        # Add inner box information
        all_boxes.extend(inner_boxes)
    
    return result, all_boxes

def find_connected_regions(matrix):
    """Find all connected regions in a matrix"""
    grid_size = matrix.shape[0]
    visited = np.zeros_like(matrix, dtype=bool)
    regions = []
    
    for i in range(grid_size):
        for j in range(grid_size):
            if matrix[i, j] and not visited[i, j]:
                # Discover a new connected region and use BFS to find all connected blocks
                region = []
                queue = [(i, j)]
                visited[i, j] = True
                
                while queue:
                    current_i, current_j = queue.pop(0)
                    region.append((current_i, current_j))
                    
                    # Check 4 adjacent directions
                    for di, dj in [(-1, 0), (0, 1), (1, 0), (0, -1)]:
                        ni, nj = current_i + di, current_j + dj
                        if (0 <= ni < grid_size and 0 <= nj < grid_size and 
                            matrix[ni, nj] and not visited[ni, nj]):
                            visited[ni, nj] = True
                            queue.append((ni, nj))
                
                if region:
                    regions.append(region)
    
    return regions

def find_surrounded_blocks(complexity_matrix, threshold=0.98):
    """Find the areas enclosed by green blocks and fill them with green

    Use the flood fill algorithm to detect enclosed areas:

    1. Start filling from the border and mark all non-green blocks that can be reached

    2. The non-green blocks that are not marked are the enclosed areas

    3. Consider 98% continuity and allow a small number of gaps in the border

    """
    grid_size = complexity_matrix.shape[0]
    
    # Create a slightly larger mesh to make it easier to work with the borders
    padded_grid = np.zeros((grid_size + 2, grid_size + 2), dtype=bool)
    
    # Copy the complexity matrix to the central area, and the surrounding area is False (indicating the outer area)
    padded_grid[1:-1, 1:-1] = complexity_matrix
    
    # Create a marker matrix to indicate whether it has been visited
    visited = np.zeros_like(padded_grid, dtype=bool)
    
    # Flood fill from external boundaries
    queue = [(0, 0)]  # Start from the top left
    visited[0, 0] = True
    
    # Four directions: up, right, down, left
    directions = [(-1, 0), (0, 1), (1, 0), (0, -1)]

    while queue:
        i, j = queue.pop(0)

        for di, dj in directions:
            ni, nj = i + di, j + dj

            if 0 <= ni < padded_grid.shape[0] and 0 <= nj < padded_grid.shape[1]:
                # If it is not visited and is not a green block, mark it as visited and add it to the queue
                if not visited[ni, nj] and not padded_grid[ni, nj]:
                    visited[ni, nj] = True
                    queue.append((ni, nj))
    
    surrounded_matrix = np.zeros_like(complexity_matrix, dtype=bool)
    
    for i in range(grid_size):
        for j in range(grid_size):
            # If it is not a green block and has not been visited after filling, it means it is an enclosed area
            if not complexity_matrix[i, j] and not visited[i+1, j+1]:
                # Further verify whether it is surrounded by green blocks with high continuity
                if is_well_surrounded(complexity_matrix, i, j, threshold):
                    surrounded_matrix[i, j] = True
    
    return surrounded_matrix

def is_well_surrounded(matrix, i, j, threshold=0.98):
    """Check if the position (i,j) is surrounded by green blocks with high continuity"""
    grid_size = matrix.shape[0]
    
    # Find the connected region containing (i,j)
    region = find_connected_region(matrix, i, j)
    
    # Checking the continuity of region boundaries
    boundary_points = find_boundary_points(matrix, region)
    green_count = 0
    
    for pi, pj in boundary_points:
        # Check if the perimeter of the boundary point is a green block
        for di, dj in [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]:
            ni, nj = pi + di, pj + dj
            if 0 <= ni < grid_size and 0 <= nj < grid_size:
                if matrix[ni, nj]: 
                    green_count += 1
                    break
    
    # Calculate the envelopment rate
    surrounding_rate = green_count / len(boundary_points) if boundary_points else 0
    return surrounding_rate >= threshold

def find_connected_region(matrix, start_i, start_j):
    """Find all non-green blocks connected to (start_i, start_j)"""
    grid_size = matrix.shape[0]
    visited = np.zeros_like(matrix, dtype=bool)
    region = []
    queue = [(start_i, start_j)]
    visited[start_i, start_j] = True
    
    while queue:
        i, j = queue.pop(0)
        region.append((i, j))
        
        for di, dj in [(-1, 0), (0, 1), (1, 0), (0, -1)]:
            ni, nj = i + di, j + dj
            if 0 <= ni < grid_size and 0 <= nj < grid_size:
                if not visited[ni, nj] and not matrix[ni, nj]:
                    visited[ni, nj] = True
                    queue.append((ni, nj))
    
    return region

def find_boundary_points(matrix, region):
    """Find the boundary points of the region (points adjacent to the green block)"""
    grid_size = matrix.shape[0]
    boundary = []
    
    for i, j in region:
        # If any of the points adjacent to this point are outside the region, then it is a boundary point.
        for di, dj in [(-1, 0), (0, 1), (1, 0), (0, -1)]:
            ni, nj = i + di, j + dj
            if not (0 <= ni < grid_size and 0 <= nj < grid_size) or matrix[ni, nj]:
                boundary.append((i, j))
                break
    
    return boundary

def is_surrounded_by_region(i, j, region_mask, grid_size):
    """Check if point (i,j) is surrounded by the region represented by region_mask"""
    directions = [(-1, 0), (0, 1), (1, 0), (0, -1)]
    is_surrounded = True
    
    for di, dj in directions:
        # Send a ray along a direction
        found_boundary = False
        ni, nj = i, j
        while 0 <= ni < grid_size and 0 <= nj < grid_size:
            ni += di
            nj += dj
            if not (0 <= ni < grid_size and 0 <= nj < grid_size) or region_mask[ni, nj]:
                found_boundary = True
                break
        
        if not found_boundary:
            is_surrounded = False
            break
    
    return is_surrounded


def process_all_images(image_path=None, images_dir=None, grid_size=32, threshold=1.5, 
                                           surrounding_threshold=0.5, 
                                           draw=1, depth=2, min_box_size=0, 
                                           model_name=None, rag=None, layout=None, block=None, dataset=None):
    """Process all images and save the results in JSON"""
    processed_images = []

    output_dir_base = f"output_{dataset}_{model_name}_rag{rag}_layout{layout}_block{block}/segments"
    if image_path is not None:
        try:
            image_path_part = image_path.split("/")[-2]
            output_dir= os.path.join(output_dir_base, image_path_part)
            os.makedirs(output_dir, exist_ok=True)

            _, output_dir = process_image(image_path, output_dir, grid_size, 
                                       threshold, surrounding_threshold, 
                                       draw, depth, min_box_size)
            processed_images.append(output_dir)
            print(f"Processing image completed: {image_path}")
        except Exception as e:
            print(f"Error while processing image: {str(e)}")
    
    elif images_dir:
        print(images_dir)
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
        image_files = []
        
        for file in os.listdir(images_dir):
            ext = os.path.splitext(file)[1].lower()
            if ext in image_extensions:
                image_files.append(file)
        
        image_path_part = images_dir.split("/")[-1]
        output_dir= os.path.join(output_dir_base, image_path_part)

        os.makedirs(output_dir, exist_ok=True)

        for image_file in tqdm.tqdm(image_files):
            input_path = os.path.join(images_dir, image_file)
            print(input_path)
            
            try:
                _, block_output_dir = process_image(input_path, output_dir, 
                                           grid_size, threshold, 
                                           surrounding_threshold, 
                                           draw, depth, min_box_size)
                processed_images.append(block_output_dir)
            except Exception as e:
                print(f"Error processing {image_file}: {str(e)}")

        print(f"All images processed. A total of {len(image_files)} images processed.")

    print(f"All results have been saved into their respective folders")

def process_images_and_save_json(args):
    """Process all images and save the results in JSON"""
    os.makedirs(args.output_dir, exist_ok=True)
    processed_images = []
    if args.image_path:
        try:
            _, output_dir = process_image(args.image_path, args.output_dir, args.grid_size, 
                                       args.threshold, args.surrounding_threshold, 
                                       args.draw, args.depth, args.min_box_size)
            processed_images.append(output_dir)
            print(f"Processing image completed: {args.image_path}")
        except Exception as e:
            print(f"Error while processing image: {str(e)}")
    
    elif args.images_dir:
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
        image_files = []
        
        for file in os.listdir(args.images_dir):
            ext = os.path.splitext(file)[1].lower()
            if ext in image_extensions:
                image_files.append(file)
        
        for image_file in tqdm.tqdm(image_files):
            input_path = os.path.join(args.images_dir, image_file)
            
            try:
                _, output_dir = process_image(input_path, args.output_dir, 
                                           args.grid_size, args.threshold, 
                                           args.surrounding_threshold, 
                                           args.draw, args.depth, args.min_box_size)
                processed_images.append(output_dir)
            except Exception as e:
                print(f"Error processing {image_file}: {str(e)}")

        print(f"All images processed. A total of {len(image_files)} images processed.")
        
    print(f"All results have been saved into their respective folders")


def main():
    parser = argparse.ArgumentParser(description='Divide the image into a grid and mark complex areas')
    parser.add_argument('--image_path', type=str, help='Path to a single input image')
    parser.add_argument('--images_dir', type=str, help='Path to the input image folder')
    parser.add_argument('--output', type=str, help='Path to a single output image')
    parser.add_argument('--output_dir', type=str, help='Path to the output image folder', default='output_boxes')
    parser.add_argument('--grid_size', type=int, default=32, help='Grid size (number of divisions)')
    parser.add_argument('--threshold', default=1.5,type=float, help='Complexity threshold')
    parser.add_argument('--draw', default=1,type=int, help='Whether to draw a line')
    parser.add_argument('--surrounding_threshold', type=float, default=0.5,
    help='Threshold of the surrounded area (between 0-1), the default 0.5 means 50% of the surrounding blocks are green')
    parser.add_argument('--depth', type=int, default=2,
    help='Connected area detection depth: 1 means only the outermost layer is detected, 2 means also the internal area is detected')
    parser.add_argument('--min_box_size', type=int, default=0,
    help='Minimum box size (number of grids), boxes smaller than this value will be ignored, the default value is 0 for no filtering')
    
    args = parser.parse_args()
    
    # Check input parameters
    if args.image_path or args.images_dir:
        process_images_and_save_json(args)
    else:
        parser.error("Either --image_path or --images_dir must be provided")

if __name__ == "__main__":
    main()
 