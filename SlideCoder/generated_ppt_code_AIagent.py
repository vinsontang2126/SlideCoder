import os
import json
from pathlib import Path
import time
import traceback
import subprocess
import tempfile
import shutil
from model import *
from utils import cleanup_response, modify_save_path
import os
from rag import *

class GenerationStats:
    def __init__(self):
        self.first_try_success = 0
        self.second_try_success = 0
        self.third_try_success = 0
        self.failed = 0
        self.total = 0
    
    def get_success_rate(self):
        success_count = self.first_try_success + self.second_try_success + self.third_try_success
        return success_count / self.total if self.total > 0 else 0
    
    def print_stats(self):
        print("\nGenerate statistics:")
        print(f"First success: {self.first_try_success}")
        print(f"Second success: {self.second_try_success}")
        print(f"Third success: {self.third_try_success}")
        print(f"Number of failures: {self.failed}")
        print(f"Total number of attempts: {self.total}")
        print(f"Success rate: {self.get_success_rate()*100:.2f}%")

class GeneratedPPTsAgent:
    def __init__(self, rag, top_n, folder_name, ppt_images_dir, descriptions_dir, 
                 model_name, layout, block, dataset):
        # Setting the base path
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.rag = rag
        self.top_n = top_n

        # Set the input directory
        self.ppt_images_dir = os.path.join(self.base_dir, folder_name)
        self.descriptions_dir = os.path.join(self.base_dir, f'output_{dataset}_{model_name}_rag{str(rag)}_layout{layout}_block{block}', 'descriptions', descriptions_dir)
        self.images_dir=os.path.join(self.base_dir, f'images_{dataset}', ppt_images_dir)
        self.background_dir=os.path.join(self.base_dir, f'background_{dataset}', ppt_images_dir)

        # Create Output Directory
        self.output_dir = os.path.join(self.base_dir, f'output_{dataset}_{model_name}_rag{str(rag)}_layout{layout}_block{block}')
        self.generated_codes_dir_base = os.path.join(self.output_dir, 'generated_codes', descriptions_dir)
        self.generated_ppts_dir_base = os.path.join(self.output_dir, 'generated_ppts', descriptions_dir)
        
        # Create a PPT comparison image directory
        self.ppt_couple_images_dir = os.path.join(self.base_dir, 'ppt_couple_images')
        
        # Create the necessary directories
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.generated_codes_dir_base, exist_ok=True)
        os.makedirs(self.generated_ppts_dir_base, exist_ok=True)
        os.makedirs(self.ppt_couple_images_dir, exist_ok=True)

        self.stats = GenerationStats()

    def get_matching_description(self, image_name):
        """Get the description file that matches the image"""
        desc_path = os.path.join(self.descriptions_dir, f'{image_name}.json')
        if os.path.exists(desc_path):
            with open(desc_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    
    def generate_code_prompt(self, image_path, description, model_name, layout):
        """Generate prompt words for AI"""
        prompt = f"""Please write Python code to create a PowerPoint slide that matches the following description:

{description['ai_description']}

"""
        
        position_content = f"""This slide contains these following details:
Position: x = {description['position']['x']*10} inches, y = {description['position']['y']*7.5} inches
Size: width = {description['size']['width']*10} inches, height ={description['size']['height']*7.5} inches
Text content: {description['ocr_text']}
Visual description: {description['ai_description']}
"""
        if layout=="True":
            prompt += position_content
        if self.rag:
            query = position_content
            if model_name in ["ppt2code", "qwenvl"]:
                rag_content = query_db(query, "./db/library.txt", self.top_n)
            else:
                rag_content = query_db(query, "./db/FBK.txt", self.top_n)
            prompt += f"""\nThe following is an introduction in python-pptx API Documentation:
{rag_content}

"""
        
        prompt += """
Please generate Python code using the python-pptx library to create a PowerPoint slide based on the provided codes. The code should:
1. Create a new PowerPoint presentation.
2. Add a slide using the slide layout with index 6 (typically a Blank Layout) to ensure a clean slate for custom content placement.
3. Include all text elements and shapes as specified in the slide, with properties such as font, size, color, and alignment accurately applied.
4. Use inches (in) units for all size and position measurements, directly converting them using python-pptx's Inches() function for shapes and positions, and Pt for font sizes.
5. Save the presentation in the output/generated_ppts directory with a descriptive filename (e.g., generated_slide.pptx).
6. Ensure the code is well-commented and handles any necessary imports.
"""
        return prompt

    def generate_debug_prompt(self, code, error_message, model_name):
        """Generate debug prompt words"""
        if self.rag:
            query = code
            if model_name in ["ppt2code", "qwenvl"]:
                rag_content = query_db(query, "./db/library.txt", self.top_n)
            else:
                rag_content = query_db(query, "./db/FBK.txt", self.top_n)
            return f"""The previous code generated an error. Please fix the code.

Error message:
{error_message}

Previous code:
```python
{code}
```

Introduction in python-pptx API Documentation:
{rag_content}

Please provide the complete corrected code that will create the PowerPoint slide successfully."""
        else:
            return f"""The previous code generated an error. Please fix the code.

Error message:
{error_message}

Previous code:
```python
{code}
```

Please provide the complete corrected code that will create the PowerPoint slide successfully."""
        

    def generate_final_code_prompt(self, generated_codes_dir, description):
        """Generate prompt words for Assembler"""
        prompt = f"""Please write Python code to create a PowerPoint slide that matches the following description:

{description['overall_description']}

"""
        if description['total_blocks']!=0:
            prompt = prompt + f"The slide contains {description['total_blocks']} blocks with the following codes:\n"
            index=0
            for root, dirs, files in os.walk(generated_codes_dir):
                for file in files:
                    if file.endswith(".py"):
                        file_path = os.path.join(root, file)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            code_content = f.read()
                            if code_content!="":
                                index=index+1
                                prompt += f"""
Block {index}:
Code: 
```python
{code_content}
```
"""
        
        prompt += """
Please generate Python code using the python-pptx library to create a PowerPoint slide based on the provided codes. The code should:
1. Create a new PowerPoint presentation.
2. Add a slide using the slide layout with index 6 (typically a Blank Layout) to ensure a clean slate for custom content placement.
3. Include all text elements and shapes as specified in the slide, with properties such as font, size, color, and alignment accurately applied.
4. Use inches (in) units for all size and position measurements, directly converting them using python-pptx's Inches() function for shapes and positions, and Pt for font sizes.
5. Save the presentation in the output/generated_ppts directory with a descriptive filename (e.g., generated_slide.pptx).
6. Ensure the code is well-commented and handles any necessary imports.
"""
        return prompt

    def generate_all_code_prompt(self, forewopic_code, background_image_path, add_images):
        prompt = f"""The following code represents part of a PowerPoint presentation, but it currently lacks background design elements and illustrative visuals. 
I will provide you with additional information about the background and illustrations.
Please help me integrate these elements into the existing PPT code accordingly.

Existing PPT Code:
```python
{forewopic_code}
```

Background path:
{background_image_path}
"""
        index=0
        for add_image in add_images:
            index=index+1
            add_image_path = add_image["image_path"]
            # Pixels to inches conversion (assuming DPI = 96)
            x_ori = add_image["coordinates"]["left"]
            y_ori = add_image["coordinates"]["top"]
            width_inch = add_image["coordinates"]["width"]
            height_inch = add_image["coordinates"]["height"]
            total_width_inch = add_image["coordinates"]["total_width"]
            total_height_inch = add_image["coordinates"]["total_height"]

            prompt += f"""
Image{index} Path:
{add_image_path}

Image{index} Coordinates:
Left: {x_ori/total_width_inch*10} inches
Top: {y_ori/total_height_inch*7.5} inches
Width: {width_inch/total_width_inch*10} inches
Height: {height_inch/total_height_inch*7.5} inches
"""
        
        prompt += """
Please generate Python code using the python-pptx library to create a PowerPoint slide based on the provided codes. The code should:
1. Create a new PowerPoint presentation.
2. Add a slide using the slide layout with index 6 (typically a Blank Layout) to ensure a clean slate for custom content placement.
3. Include all text elements and shapes as specified in the slide, with properties such as font, size, color, and alignment accurately applied.
4. Use inches (in) units for all size and position measurements, directly converting them using python-pptx's Inches() function for shapes and positions, and Pt for font sizes.
5. Save the presentation in the output/generated_ppts directory with a descriptive filename (e.g., generated_slide.pptx).
6. Ensure the code is well-commented and handles any necessary imports.
"""
        return prompt

    def add_images_background(self, image_name, model_name):
        self.stats.total += 1
        generated_codes_dir=os.path.join(self.generated_codes_dir_base, image_name)
        success = False
        last_error = None
        code_path = None
        max_tries = 5
        current_try = 0
        while not success and current_try <= max_tries:
            forewopic_code_filename = f'{image_name}_forewopic_final_code.py'
            forewopic_code_path = os.path.join(generated_codes_dir, forewopic_code_filename)
            background_image_path = os.path.join(self.background_dir, f'{image_name}.png')
            images_image_json = os.path.join(self.images_dir, "image_metadata.json")
            print("images_image_json path : "+images_image_json)
            os.makedirs(generated_codes_dir, exist_ok=True)
            add_images = []
            try:
                with open(images_image_json, 'r') as file:
                    data = json.load(file)
                    for image_message in data:
                        slide_number=str(image_message["slide_number"])
                        image_index = str(image_message["image_index"])
                        coordinates = image_message["coordinates"]
                        images_image_path = os.path.join(self.images_dir, f'image_{image_index}.png')
                        add_images.append({
                            "image_path":images_image_path,
                            "coordinates":coordinates
                        })
            except FileNotFoundError:
                print(f"{images_image_json} Does not exist")
            except json.JSONDecodeError:
                print(f"{images_image_json} JSON format error")
            except Exception as e:
                print(f"An unknown error occurred: {str(e)}")
            
            with open(forewopic_code_path, 'r') as file:
                forewopic_code = file.read()     
            current_try += 1
            try:
                if current_try == 1:
                    prompt = self.generate_all_code_prompt(forewopic_code, background_image_path, add_images)
                    print("The Assembler prompt is : "+"-"*100)
                    print(prompt)
                    print("The Assembler prompt over : "+"-"*100)
                    if model_name == "gemini":
                        response = gemini_final_call(prompt=prompt)
                    elif model_name == "claude":
                        response = claude_call(prompt=prompt)
                    elif model_name in ["qwenvl"]:
                        response = qwenvl_final_call(prompt=prompt)
                    elif model_name in ["ppt2code"]:
                        response = ppt2code_final_call(prompt=prompt)
                    else:
                        response = gpt_final_call(prompt=prompt)
                else:
                    with open(code_path, 'r', encoding='utf-8') as f:
                        failed_code = f.read()
                    
                    debug_prompt = self.generate_debug_prompt(failed_code, last_error, model_name)
                    print("The Stage 4 final debug code prompt is : "+"-"*100)
                    print(debug_prompt)
                    print("The Stage 4 final debug code prompt over : "+"-"*100)
                    
                    if model_name == "gemini":
                        response = gemini_final_call(prompt=debug_prompt)
                    elif model_name == "claude":
                        response = claude_call(prompt=debug_prompt)
                    elif model_name == "qwenvl":
                        response = qwenvl_final_call(prompt=debug_prompt)
                    elif model_name in ["ppt2code"]:
                        response = ppt2code_final_call(prompt=debug_prompt)
                    else:
                        response = gpt_final_call(prompt=debug_prompt)

                code = self.cleanup_response(response)
                code_filename = f'{image_name}_allphoto_final_code.py'
                code_path = os.path.join(generated_codes_dir, code_filename)
                history_dir = os.path.join(self.base_dir, 'history')
                os.makedirs(history_dir, exist_ok=True)
                model_history_dir = os.path.join(history_dir, model_name)
                os.makedirs(model_history_dir, exist_ok=True)
                image_stem = image_name
                history_filename = f'{image_stem}_all_final_code_{time.strftime("%Y%m%d_%H%M%S")}.json'
                history_path = os.path.join(model_history_dir, history_filename)
                with open(history_path, 'w', encoding='utf-8') as f:
                    json.dump({'prompt': prompt, 'response': response}, f)

                code = modify_save_path(code, code_path)
                code = code.replace(
                    './generated_ppts', 
                    os.path.join('output', f'generated_ppts/{image_name}')
                )
                with open(code_path, 'w', encoding='utf-8') as f:
                    f.write(code)
                generated_ppts_dir=os.path.join(self.generated_ppts_dir_base, image_name)
                os.makedirs(generated_ppts_dir, exist_ok=True)
                success, error_message = self.run_code(code_path)
                if success:
                    if current_try == 1:
                        self.stats.first_try_success += 1
                    elif current_try == 2:
                        self.stats.second_try_success += 1
                    else:
                        self.stats.third_try_success += 1
                    print(f"Attempt {current_try} succeeded!")
                    success = True
                    break
                else:
                    last_error = error_message
                    print(f"Attempt {current_try} failed: {error_message}")

            except Exception as e:
                last_error = str(e)
                print(f"Error at attempt {current_try}: {str(e)}")

        if not success:
            self.stats.failed += 1
            print(f"Failed to generate PPT for {image_name}. The maximum number of attempts has been reached.")
            return False

    def add_images_background_ft(self, image_name, model_name):
        """Add bg and images"""
        self.stats.total += 1
        generated_codes_dir=os.path.join(self.generated_codes_dir_base, image_name)
        success = False
        last_error = None
        code_path = None
        current_try = 0
        forewopic_code_filename = f'{image_name}_forewopic_final_code.py'
        forewopic_code_path = os.path.join(generated_codes_dir, forewopic_code_filename)
        background_image_path = os.path.join(self.background_dir, f'{image_name}.png')
        images_image_json = os.path.join(self.images_dir, "image_metadata.json")
        print("images_image_json path : "+images_image_json)
        os.makedirs(generated_codes_dir, exist_ok=True)
        add_images = []
        try:
            with open(images_image_json, 'r') as file:
                data = json.load(file)
                for image_message in data:
                    slide_number=str(image_message["slide_number"])
                    image_index = str(image_message["image_index"])
                    coordinates = image_message["coordinates"]
                    images_image_path = os.path.join(self.images_dir, f'image_{image_index}.png')
                    add_images.append({
                        "image_path":images_image_path,
                        "coordinates":coordinates
                    })
        except FileNotFoundError:
            print(f"The file {images_image_json} does not exist")
        except json.JSONDecodeError:
            print(f"The JSON format of the file {images_image_json} is incorrect")
        except Exception as e:
            print(f"An unknown error occurred: {str(e)}")
        with open(forewopic_code_path, 'r') as file:
            forewopic_code = file.read()     
        parts_forewopic_code = forewopic_code.split("slide = prs.slides.add_slide(slide_layout)")

        bg_code=f"""
# Add slide background
background_picture = slide.shapes.add_picture(
    r'{background_image_path}',
    0,
    0,
    prs.slide_width,
    prs.slide_height
)
background_picture.zorder = 0
"""
        image_code=""
        for image in add_images:
            x_ori = image["coordinates"]["left"]
            y_ori = image["coordinates"]["top"]
            width_inch = image["coordinates"]["width"]
            height_inch = image["coordinates"]["height"]
            total_width_inch = image["coordinates"]["total_width"]
            total_height_inch = image["coordinates"]["total_height"]
            image_code +=f"""
slide.shapes.add_picture(
    r'{image["image_path"]}',
    left=prs.slide_width * {x_ori/total_width_inch},
    top=prs.slide_height * {y_ori/total_height_inch},
    width=prs.slide_width * {width_inch/total_width_inch},
    height=prs.slide_height * {height_inch/total_height_inch}
)
"""
        final_code = parts_forewopic_code[0] + "slide = prs.slides.add_slide(slide_layout)" +bg_code + image_code + parts_forewopic_code[1]
        code_filename = f'{image_name}_allphoto_final_code.py'
        code_path = os.path.join(generated_codes_dir, code_filename)
        image_stem = image_name
        final_code = modify_save_path(final_code, code_path)
        final_code = final_code.replace(
            './generated_ppts', 
            os.path.join('output', f'generated_ppts/{image_name}')
        )
        with open(code_path, 'w', encoding='utf-8') as f:
            f.write(final_code)
        generated_ppts_dir=os.path.join(self.generated_ppts_dir_base, image_name)
        os.makedirs(generated_ppts_dir, exist_ok=True)
        success, error_message = self.run_code(code_path)
        if success:
            if current_try == 1:
                self.stats.first_try_success += 1
            elif current_try == 2:
                self.stats.second_try_success += 1
            else:
                self.stats.third_try_success += 1
            print(f"The {current_try}th attempt succeeded!")
            success = True
        else:
            last_error = error_message
            print(f"{current_try}th attempt failed: {error_message}")

        
    def cleanup_response(self, response):
        """Clean up the response and extract the code part"""
        # Use the cleanup_response function in utils
        code = cleanup_response(response)
        code = code.replace("./generated_ppts", os.path.join('output', "generated_ppts"))
        return code

    def run_code(self, code_path):
        """Execute the generated Python code"""
        try:
            with open(code_path, 'r', encoding='utf-8') as f:
                code = f.read()
            exec(code)
            return True, None
        except Exception as e:
            error_message = traceback.format_exc()
            return False, error_message


    def process_image(self, image_name, model_name=None, layout="True"):
        """Processing a single image"""
        self.stats.total += 1
        image_path = os.path.join(self.ppt_images_dir, image_name, f"{image_name}_original.png")
        print(image_path)
        description = self.get_matching_description(image_name)     
        if not description:
            print(f"No description file found for image {image_name}")
            self.stats.failed += 1
            return False
        last_error = None
        code_path = None
        blocks=description["blocks"]
        print(len(blocks))
        index=0
        for block in blocks:
            index = index+1
            max_tries = 5
            current_try = 0
            success = False
            block_image_path = os.path.join(self.ppt_images_dir, image_name, f"{image_name}_box{index}.png")
            while not success and current_try <= max_tries:
                current_try += 1
                print(f"{index}BLOCK Try to {current_try} times...")
                try:
                    if current_try == 1:
                        prompt = self.generate_code_prompt(block_image_path, block, model_name, layout)
                        print("Coder start "+"-"*100)
                        print(prompt)
                        print("Coder end "+"-"*100)
                        print(model_name)
                        if model_name == "gemini":
                            response = gemini_call(prompt=prompt, image_path=block_image_path)
                        elif model_name == "claude":
                            response = claude_call(prompt=prompt, image_path=block_image_path)
                        elif model_name == "qwenvl":
                            response = qwenvl_call(prompt=prompt, image_path=block_image_path)
                        elif model_name in ["ppt2code"]:
                            response = ppt2code_call(prompt=prompt, image_path=block_image_path)
                        elif model_name == "gpt":
                            response = gpt_call(prompt=prompt, image_path=block_image_path)
                        else: 
                            raise Exception('Method Error!')
                    else:
                        # Subsequent attempts - Fixing the code
                        with open(code_path, 'r', encoding='utf-8') as f:
                            failed_code = f.read()
                        debug_prompt = self.generate_debug_prompt(failed_code, last_error, model_name)
                        print("Debug Agent2 "+"-"*100)
                        print(debug_prompt)
                        print("Debug Agent2 "+"-"*100)
                        if model_name == "gemini":
                            response = gemini_call(prompt=debug_prompt, image_path=block_image_path)
                        elif model_name == "claude":
                            response = claude_call(prompt=debug_prompt, image_path=block_image_path)
                        elif model_name == "qwenvl":
                            response = qwenvl_call(prompt=debug_prompt, image_path=block_image_path)
                        elif model_name in ["ppt2code"]:
                            response = ppt2code_call(prompt=debug_prompt, image_path=block_image_path)
                        elif model_name == "gpt":
                            response = gpt_call(prompt=debug_prompt, image_path=block_image_path)
                        else:
                            raise Exception('Method Error!')
                    # Clean the response and save the code
                    code = self.cleanup_response(response)
                    code_filename = f'{image_name}_block_{index}.py'
                    generated_codes_dir=os.path.join(self.generated_codes_dir_base, image_name)
                    print(generated_codes_dir)
                    os.makedirs(generated_codes_dir, exist_ok=True)
                    code_path = os.path.join(generated_codes_dir, code_filename)
                    history_dir = os.path.join(self.base_dir, 'history')
                    os.makedirs(history_dir, exist_ok=True)
                    model_history_dir = os.path.join(history_dir, model_name)
                    os.makedirs(model_history_dir, exist_ok=True)
                    history_filename = f'{image_name}_block_{index}_{time.strftime("%Y%m%d_%H%M%S")}.json'
                    history_path = os.path.join(model_history_dir, history_filename)
                    with open(history_path, 'w', encoding='utf-8') as f:
                        json.dump({'prompt': prompt, 'response': response}, f)
                    # Modify the save path
                    code = modify_save_path(code, code_path)
                    code = code.replace(
                        './generated_ppts', 
                        os.path.join('output', f'generated_ppts/{image_name}')
                    )
                    print("Agent code start " + "$"*100)
                    print(code)
                    print("Agent code over " + "$"*100)                 
                    with open(code_path, 'w', encoding='utf-8') as f:
                        f.write(code)
                    generated_ppts_dir=os.path.join(self.generated_ppts_dir_base, image_name)
                    os.makedirs(generated_ppts_dir, exist_ok=True)
                    success, error_message = self.run_code(code_path)
                    if success:
                        if current_try == 1:
                            self.stats.first_try_success += 1
                        elif current_try == 2:
                            self.stats.second_try_success += 1
                        else:
                            self.stats.third_try_success += 1
                        print(f"{current_try} Time Work")
                        success = True
                        break
                    else:
                        last_error = error_message
                        if current_try == max_tries:
                            with open(code_path, 'w', encoding='utf-8') as f:
                                    f.write("")
                        print(f"{current_try} failed attempts: {error_message}")

                except Exception as e:
                    last_error = str(e)
                    print(f"{current_try} Attempts failed: {str(e)}")

        return True


    def produce_final_code_image(self, image_name, model_name=None, block=None):
        self.stats.total += 1
        image_path = os.path.join(self.ppt_images_dir, image_name)
        description = self.get_matching_description(image_name)
        generated_codes_dir=os.path.join(self.generated_codes_dir_base, image_name)
        if not description:
            print(f"No description file found for image {image_name}")
            self.stats.failed += 1
            return False
        success = False
        last_error = None
        code_path = None
        max_tries = 1
        current_try = 0
        while not success and current_try <= max_tries:
            current_try += 1
            print(f"Trying {current_try} Time generation...")
            try:
                if current_try == 1:
                    prompt = self.generate_final_code_prompt(generated_codes_dir, description)
                    print("The Agent3 code prompt is : "+"-"*100)
                    print(prompt)
                    print("The Agent code prompt over : "+"-"*100)
                    if block=="True":
                        if model_name == "gemini":
                            response = gemini_final_call(prompt=prompt)
                        elif model_name == "claude":
                            response = claude_call(prompt=prompt)
                        elif model_name == "qwenvl":
                            response = qwenvl_final_call(prompt=prompt)
                        elif model_name in ["ppt2code"]:
                            response = ppt2code_final_call(prompt=prompt)
                        elif model_name == "gpt":
                            response = gpt_final_call(prompt=prompt)
                        else:
                            raise Exception('Method Error!')
                    else:
                        block_image_path = description["image_path"]
                        if model_name == "gemini":
                            response = gemini_call(prompt=prompt, image_path=block_image_path)
                        elif model_name == "claude":
                            response = claude_call(prompt=prompt, image_path=block_image_path)
                        elif model_name == "qwenvl":
                            response = qwenvl_call(prompt=prompt, image_path=block_image_path)
                        elif model_name in ["ppt2code"]:
                            response = ppt2code_call(prompt=prompt, image_path=block_image_path)
                        elif model_name == "gpt":
                            response = gpt_call(prompt=prompt, image_path=block_image_path)
                        else:
                            raise Exception('Method Error!')

                else:
                    # Subsequent attempts - Fixing the code
                    with open(code_path, 'r', encoding='utf-8') as f:
                        failed_code = f.read()
                    debug_prompt = self.generate_debug_prompt(failed_code, last_error, model_name)
                    print("Assembler debug code prompt is : "+"-"*100)
                    print(debug_prompt)
                    print("Assembler debug code prompt over : "+"-"*100)
                    if model_name == "gemini":
                        response = gemini_final_call(prompt=debug_prompt)
                    elif model_name == "claude":
                        response = claude_call(prompt=debug_prompt)
                    elif model_name == "qwenvl":
                        response = qwenvl_final_call(prompt=debug_prompt)
                    elif model_name in ["ppt2code"]:
                        response = ppt2code_final_call(prompt=debug_prompt)
                    elif model_name == "gpt":
                        response = gpt_final_call(prompt=debug_prompt)
                    else:
                        raise Exception('Method Error!')

                # Clean up the response and save the final code generated by Agent3
                code = self.cleanup_response(response)
                code_filename = f'{image_name}_forewopic_final_code.py'
                code_path = os.path.join(generated_codes_dir, code_filename)
                os.makedirs(generated_codes_dir, exist_ok=True)
                history_dir = os.path.join(self.base_dir, 'history')
                os.makedirs(history_dir, exist_ok=True)
                model_history_dir = os.path.join(history_dir, model_name)
                os.makedirs(model_history_dir, exist_ok=True)
                image_stem = image_name
                history_filename = f'{image_stem}_block_final_code_{time.strftime("%Y%m%d_%H%M%S")}.json'
                history_path = os.path.join(model_history_dir, history_filename)
                with open(history_path, 'w', encoding='utf-8') as f:
                    json.dump({'prompt': prompt, 'response': response}, f)

                code = modify_save_path(code, code_path)
                code = code.replace(
                    './generated_ppts', 
                    os.path.join('output', f'generated_ppts/{image_name}')
                )       
                with open(code_path, 'w', encoding='utf-8') as f:
                    f.write(code)
                generated_ppts_dir=os.path.join(self.generated_ppts_dir_base, image_name)
                os.makedirs(generated_ppts_dir, exist_ok=True)
                # Executing Code
                success, error_message = self.run_code(code_path)
                if success:
                    if current_try == 1:
                        self.stats.first_try_success += 1
                    elif current_try == 2:
                        self.stats.second_try_success += 1
                    else:
                        self.stats.third_try_success += 1
                    print(f"Attempt {current_try} succeeded!")
                    success = True
                    break
                else:
                    last_error = error_message
                    print(f"Attempt {current_try} failed: {error_message}")

            except Exception as e:
                last_error = str(e)
                print(f"Error at attempt {current_try}: {str(e)}")

        if not success:
            self.stats.failed += 1
            print(f"Failed to generate PPT for {image_name}. The maximum number of attempts has been reached.")
            return False
        
        return True

    def process_all_images(self, model_name="qwenvl", layout="True", block="True"):
        """Process all images"""
        image_files = [f for f in os.listdir(self.ppt_images_dir) 
                      if os.path.isdir(os.path.join(self.ppt_images_dir, f))]
        print(image_files)
        for image_file in image_files:
            print(f"\nProcessing images: {image_file}")
            if block=="True": # Only when the blocks are divided will the content of each block be generated
                result = self.process_image(image_file, model_name, layout) # Coder
            final_code = self.produce_final_code_image(image_file, model_name, block) # Assembler
            if model_name == "ppt2code":
                self.add_images_background_ft(image_file, model_name) # Assembler
            else:
                self.add_images_background(image_file, model_name) # Assembler
        self.stats.print_stats()

def main():
    rag = True
    agent = GeneratedPPTsAgent(rag)
    agent.process_all_images(model_name="gpt")

if __name__ == "__main__":
    main()


# python generated_ppt_code_AIagent.py

