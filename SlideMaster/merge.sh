nohup llamafactory-cli export examples/merge_lora/qwen2_5vl_lora_sft.yaml \
    > "MERGE_$(date +'%y%m%d_%H%M')_qwen2_5vl_pp2code.log" 2>&1 &




# llamafactory-cli merge examples/merge_lora/qwen2vl_lora_sft.yaml