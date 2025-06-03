CUDA_VISIBLE_DEVICES=5,6,7 nohup llamafactory-cli train examples/train_lora/qwen2_5vl_lora_sft.yaml \
    > "AAA_$(date +'%y%m%d_%H%M')_qwen2vl_pp2code.log" 2>&1 &



# bash train.sh