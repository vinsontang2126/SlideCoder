#!/bin/bash
set -e

models=${1:-"gpt"}
rags=${2:-"True"}
top_ns=${3:-3}
folder_names=${4:-"design"}
layout=${5:-"True"}
block=${6:-"True"}
dataset=${7:-"ours"}
IFS=","

for model in $models; do
    for rag in $rags; do
        for top_n in $top_ns; do
            for folder_name in $folder_names; do
                date +"%Y-%m-%d %H:%M:%S"
                echo "Model: ${model}"
                echo "RAG: ${rag}"
                echo "top_n: ${top_n}"
                echo "folder_names: ${folder_name}"
                echo "Layout: ${layout}"
                echo "Block: ${block}"
                echo "Dataset: ${dataset}"
                log_file="main_${model}_Dataset${dataset}_RAG${rag}_Layout${layout}_Block${block}_$(date +'%y%m%d_%H%M%S').log"

                nohup python ./main.py \
                    --model "${model}" \
                    --rag "${rag}" \
                    --top_n "${top_n}" \
                    --folder_name "${folder_name}" \
                    --layout "${layout}" \
                    --block "${block}" \
                    --dataset "${dataset}" \
                    > "./logs/${log_file}" 2>&1 &
            done
        done
    done
done


# bash scripts/main.sh