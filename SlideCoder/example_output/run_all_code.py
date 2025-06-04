wrong=0

code_path="generated_codes/{number}/{number}/{number}_allphoto_final_code.py"

code_path_new="generated_codes/{number}/{number}/{number}_work.py"

for num in range(300):
    index=str(num+1)
    print(index)
    file_name=code_path.format(number=index)
    new_file_name=code_path_new.format(number=index)
    try:
        with open(file_name, 'r', encoding='utf-8') as file:
            original_content = file.read()

        code_to_insert = """import os
os.makedirs("output", exist_ok=True)
"""
        modified_content = original_content.replace(f"output/generated_ppts/{index}/{index}_allphoto_final_code.pptx", 
                                                    f"output/{index}_all_final_code.pptx")

        if modified_content.find(f"output/{index}_all_final_code.pptx")==-1:
            modified_content = modified_content + f"\npresentation.save(\"output/{index}_all_final_code.pptx\")"
        modified_content = code_to_insert + modified_content

        with open(new_file_name, 'w', encoding='utf-8') as file:
            file.write(modified_content)

        try:
            exec(modified_content)
        except Exception as e:
            print(f"An error occurred while running the modified code: {e}")

    except FileNotFoundError:
        print(f"File {file_name} does not exist, skipping processing.")
        wrong=wrong+1

print(wrong)

print(wrong/300)
