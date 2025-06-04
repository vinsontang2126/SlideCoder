import os
import cv2
import json
from model import *
from PIL import Image
from rag import *


class PPTDescriptionAgent:
    def __init__(self, rag, top_n, model_name, layout, block, dataset):
        # Initialize the output directory structure
        self.output_base_dir = f'output_{dataset}_{model_name}_rag{str(rag)}_layout{layout}_block{block}'
        self.descriptions_dir = os.path.join(self.output_base_dir, 'descriptions')
        self.rag = rag
        self.top_n = top_n

        # Create the necessary directories
        os.makedirs(self.descriptions_dir, exist_ok=True)

    def process_ppt_folder(self, folder_path, model_name, block, dataset):
        """Process all PPT pictures in the folder"""
        image_files = [f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))]
        for image_file in image_files:
            # Create a corresponding segments folder for each image
            image_name = f"{image_file}_original.png"            
            # Processing a single complete image
            image_path = os.path.join(folder_path, image_file, image_name)
            print(f"Processing image: {image_path}")
            dir_name = image_path.split("/")[-3]
            # if dataset =="Slide2Code":
            #     self.process_ppt_image(image_path, image_file, model_name, dir_name, block)
            # elif dataset == "slidebench":
            #     self.process_ppt_image_slidebench(image_path, image_file, model_name, dir_name, block)
            # else:
            #     raise ValueError("dataset don't exist")
            self.process_ppt_image_slidebench(image_path, image_file, model_name, dir_name, block)

    def process_ppt_image(self, image_path, image_name, model_name, dir_name, ifblock):
        """Processing a single PPT image"""
        description_json =f"./descriptions_gpt/{image_name}/{image_name}.json"
        with open(description_json, 'r', encoding='utf-8') as file:
            description_data = json.load(file)
        
        # Split the image and get block information 
        json_file=image_path.split("_original")[0]+"_info.json"
        with open(json_file, 'r', encoding='utf-8') as file:
            data = json.load(file)
 
        blocks=data["boxes"]
        image_size=data["image_size"]   
        # Processing details for each block
        detailed_blocks = []
        output_json_dir=os.path.join(self.descriptions_dir, dir_name)
        os.makedirs(output_json_dir, exist_ok=True)
        for idx, block in enumerate (blocks):
            # Extract the original coordinates and size for scaling
            x_i = block['position'][2]
            y_i = block['position'][0]
            w_i = block["size"]["width"]
            h_i = block["size"]["height"]
            x = x_i/image_size["width"]
            y = y_i/image_size["height"]
            w = w_i/image_size["width"]
            h = h_i/image_size["height"]
            block_path=image_path.split("_original")[0]+f"_box{str(idx+1)}.png"
            block_info = {
                "block_id": idx,
                "position": {
                    "x": x,
                    "y": y
                },
                "size": {
                    "width": w,
                    "height": h
                },
                "ocr_text": description_data["blocks"][idx]["ocr_text"],
                "ai_description": description_data["blocks"][idx]["ai_description"]
            }
            detailed_blocks.append(block_info)
        
        # Save the complete description
        if ifblock=="True":
            result = {
                "image_path": image_path,
                "total_blocks": len(blocks),
                "overall_description": description_data["overall_description"],
                "blocks": detailed_blocks
            }
        else:
            result = {
                "image_path": image_path,
                "total_blocks": 0,
                "overall_description": description_data["overall_description"],
                "blocks": []
            }
        
        # Save to JSON file, using the original image name
        output_json = os.path.join(output_json_dir, f'{image_name}.json')
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
            
        return result

    def process_ppt_image_slidebench(self, image_path, image_name, model_name, dir_name, ifblock):
        """Processing a single PPT image"""
        if self.rag:
            query = "Please provide a detailed description of this PPT screenshot, including its overall content and layout. Describe how different sections are arranged and what main content each section contains."
            rag_content = query_db(query, "./db/TBK.txt", self.top_n)
            overall_prompt = f"""Please provide a detailed description of this PPT screenshot, including its overall content and layout. Describe how different sections are arranged and what main content each section contains.
The following is an introduction to layout shape types in PPT:
{rag_content}"""
        else:
            overall_prompt = "Please provide a detailed description of this PPT screenshot, including its overall content and layout. Describe how different sections are arranged and what main content each section contains."
        print("ALL PPT Agent1 start " + "-" * 100)
        print(overall_prompt)
        print("ALL PPT Agent1 end " + "-" * 100)
        if model_name == "gemini":
            overall_description = gemini_call(prompt=overall_prompt, image_path=image_path)
        elif model_name == "claude":
            overall_description = claude_call(prompt=overall_prompt, image_path=image_path)
        elif model_name == "ppt2code":
            overall_description = ppt2code_call(prompt=overall_prompt, image_path=image_path)
        elif model_name == "gpt":
            overall_description = gpt_call(prompt=overall_prompt, image_path=image_path)
        else:
            raise NameError("model name don't exist")
        
        json_file=image_path.split("_original")[0]+"_info.json"
        with open(json_file, 'r', encoding='utf-8') as file:
            data = json.load(file)
        blocks=data["boxes"]
        image_size=data["image_size"]
        # Processing details for each block
        detailed_blocks = []
        output_json_dir=os.path.join(self.descriptions_dir, dir_name)
        os.makedirs(output_json_dir, exist_ok=True)
        for idx, block in enumerate (blocks):
            x_i = block['position'][2]
            y_i = block['position'][0]
            w_i = block["size"]["width"]
            h_i = block["size"]["height"]
            x = x_i/image_size["width"]
            y = y_i/image_size["height"]
            w = w_i/image_size["width"]
            h = h_i/image_size["height"]
            block_path=image_path.split("_original")[0]+f"_box{str(idx+1)}.png"
            block_info = {
                "block_id": idx,
                "position": {
                    "x": x,
                    "y": y
                },
                "size": {
                    "width": w,
                    "height": h
                },
                "ocr_text": self._get_easyocr_text(block_path),
                "ai_description": self._get_block_description(block_path, model_name)
            }
            detailed_blocks.append(block_info)
        
        # Save the complete description
        if ifblock=="True":
            result = {
                "image_path": image_path,
                "total_blocks": len(blocks),
                "overall_description": overall_description,
                "blocks": detailed_blocks
            }
        else:
            result = {
                "image_path": image_path,
                "total_blocks": 0,
                "overall_description":overall_description,
                "blocks": []
            }
        # Save the complete description
        result = {
            "image_path": image_path,
            "total_blocks": len(blocks),
            "overall_description": overall_description,
            "blocks": detailed_blocks
        }
        
        # Save to JSON file, using the original image name
        output_json = os.path.join(output_json_dir, f'{image_name}.json')
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
            
        return result
    
    def _get_easyocr_text(self, block_image):
        """Recognize text using EASTOCR"""
        try:
            import easyocr
            reader = easyocr.Reader(['ch_sim','en']) # this needs to run only once to load the model into memory
            result = reader.readtext(block_image, detail = 0)
            ocr_result=""
            for item in result:
                ocr_result=ocr_result+item+"\n"
            return ocr_result.strip()
        except Exception as e:
            print(f"OCR ERROR: {str(e)}")
            return ""

    def _get_block_description(self, block_image_path, model_name):
        """Get the AI ​​description of a single block"""
        if self.rag:
            query="Please describe this region in detail, including its textual content, graphical elements, and layout structure. Analyze both the content and its visual presentation."
            rag_content = query_db(query, "./db/TBK.txt", self.top_n)
            prompt = f"""Please describe this region in detail, including its textual content, graphical elements, and layout structure. Analyze both the content and its visual presentation.
The following is an introduction to layout shape types in PPT:
{rag_content}"""
        else:
            prompt = "Please describe this region in detail, including its textual content, graphical elements, and layout structure. Analyze both the content and its visual presentation."
        
        print("Block Agent1 start "+"-"*100)
        print(prompt)
        print("Block Agent1 end "+"-"*100)
        try:
            if model_name == "gemini":
                description = gemini_call(prompt=prompt, image_path=block_image_path)
            elif model_name == "claude":
                description = claude_call(prompt=prompt, image_path=block_image_path)
            elif model_name in ["qwen-vl"]:
                description = qwenvl_call(prompt=prompt, image_path=block_image_path)
            elif model_name in ["ppt2code"]:
                description = ppt2code_call(prompt=prompt, image_path=block_image_path)
            elif model_name == "gpt":
                description = gpt_call(prompt=prompt, image_path=block_image_path)
            else:
                raise TypeError("model name don't exist")
            
            return description
        except Exception as e:
            print(f"Error getting block description: {str(e)}")
            return ""

def main():
    rag = False
    model_name = "gpt"
    agent = PPTDescriptionAgent(rag)
    folder_path = "blue_data"
    agent.process_ppt_folder(folder_path, model_name)
    print(f"Processing completed! All description files have been saved to: {os.path.join(agent.descriptions_dir)}")

if __name__ == "__main__":
    main()


# python get_description_AIagent.py