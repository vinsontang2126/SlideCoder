from get_description_AIagent import PPTDescriptionAgent
from generated_ppt_code_AIagent import GeneratedPPTsAgent
from block_based import *
import os
import argparse
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed


def complete_item(args, image_dir_name, index):
    logging.debug("-------------------------------------------")
    logging.info(f"### Start Index: {index}")
    if args.rag=="True":
        rag=True
        print("$"*100)
    else:
        rag=False
        print("$"*100)

    model_name = args.model
    print(f"args.folder_name = {args.folder_name!r}")
    print(f"image_dir_name = {image_dir_name!r}")
    path = f"output_{args.dataset}_{args.model}_rag{args.rag}_layout{args.layout}_block{args.block}/generated_codes/{image_dir_name}/{image_dir_name}/{image_dir_name}_allphoto_final_code.py"
    
    if os.path.exists(path):
        print(f"The path {path} exists")
    else:
        image_dir = os.path.join(args.folder_name, image_dir_name)
        # Range Segmentation
        process_all_images(images_dir=image_dir, model_name=model_name, 
                            rag=args.rag, layout=args.layout, block=args.block, dataset=args.dataset)
        # Describer
        agent_one = PPTDescriptionAgent(rag, args.top_n, model_name, args.layout, args.block, args.dataset)
        folder_name = os.path.join(f'output_{args.dataset}_{args.model}_rag{args.rag}_layout{args.layout}_block{args.block}', 'segments', image_dir_name)
        agent_one.process_ppt_folder(folder_name, model_name=args.model, block=args.block, dataset=args.dataset)
        print(f"Processing completed! All description files have been saved to: {os.path.join(agent_one.descriptions_dir, image_dir_name)}")

        # Coder and Assembler
        agent_two = GeneratedPPTsAgent(rag, args.top_n, folder_name, image_dir_name, 
                                        image_dir_name, model_name, args.layout, args.block, args.dataset)
        agent_two.process_all_images(model_name=args.model, layout=args.layout, block=args.block)

        return 1

def main(args):

    output = complete_item(args, "284", "284")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="gpt", type=str)
    parser.add_argument("--rag", default="False", type=str)
    parser.add_argument("--top_n", default=1, type=int)
    parser.add_argument("--folder_name", default="design", type=str)
    parser.add_argument("--num_threads", default=1, type=int)
    parser.add_argument("--layout", default="True", type=str)
    parser.add_argument("--block", default="True", type=str)
    parser.add_argument("--dataset", default="Slide2Code", type=str)

    args = parser.parse_args()
    args.folder_name = f"../Slide2Code/input/{args.folder_name}"
    main(args)


# python main.py