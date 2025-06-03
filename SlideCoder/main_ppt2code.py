from get_description_AIagent import PPTDescriptionAgent
from generated_ppt_code_AIagent import GeneratedPPTsAgent
from block_based import *
import os
import argparse
import logging

def main(args):
    if args.rag=="True":
        rag=True
        print("$"*100)
    else:
        rag=False
        print("$"*100)
    
    model_name = args.model
    # Range Segmentation
    for image_dir_name in os.listdir(args.folder_name):
        print(image_dir_name)
        path = f"output_{args.model}/segments/{image_dir_name}"
        if os.path.exists(path):
            if os.path.isdir(path):
                print(f"The directory {path} exists.")
            else:
                print(f"The path {path} exists, but it is not a directory.")
        else:
            print(f"The directory {path} does not exist.")
            image_dir = os.path.join(args.folder_name, image_dir_name)
            print(f"Start processing all photos under {image_dir_name}📂")
            print(image_dir)
            # Start segmenting the image
            process_all_images(images_dir=image_dir, model_name=model_name)
            # Describer
            agent_one = PPTDescriptionAgent(rag, args.top_n, model_name)
            folder_name = image_dir
            folder_name = os.path.join(f'output_{args.model}', 'segments', image_dir_name)
            agent_one.process_ppt_folder(folder_name, model_name=args.model)
            print(f"Processing completed! All description files have been saved to: {os.path.join(agent_one.descriptions_dir, image_dir_name)}")
            # Coder and Assembler
            agent_two = GeneratedPPTsAgent(rag, args.top_n, folder_name, image_dir_name, image_dir_name, model_name)
            agent_two.process_all_images(model_name=args.model)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="ppt2code", type=str)
    parser.add_argument("--rag", default="False", type=str)
    parser.add_argument("--top_n", default=1, type=int)
    parser.add_argument("--folder_name", default="forewopic", type=str)

    args = parser.parse_args()
    main(args)


# python main_ppt2code.py