import time
from utils import *
import os
import retry
from openai import OpenAI
import base64
import requests
import json
import random
from vllm import LLM, SamplingParams
import PIL

openai_client = OpenAI(
                api_key="sk-pLc2dKFCKIhFrtXUD666C55605Fa4aD7Af2cEc30C560AfA7",
                base_url="https://openkey.cloud/v1")


@retry.retry(tries=5, delay=2)
def gemini_call(prompt, image_path, image_path2=None):
    try:
        api_key = ""
        
        gemini_client = OpenAI(
            api_key = api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        # Convert image to base64
        image_data = encode_image(image_path)
        response = gemini_client.chat.completions.create(
            model="gemini-2.0-flash",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=4096,
            temperature=0
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Gemini call error: {str(e)}")
        raise


@retry.retry(tries=5, delay=2)
def gemini_final_call(prompt, image_path2=None):
    try:
        api_key = ""
        gemini_client = OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        response = gemini_client.chat.completions.create(
            model="gemini-2.0-flash",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt}
                    ]
                }
            ],
            max_tokens=4096,
            temperature=0
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Gemini call error: {str(e)}")
        raise

@retry.retry(tries=5, delay=2)
def qwenvl_call(prompt, image_path, image_path2=None):
    try:
        openai_api_key = "EMPTY"
        openai_api_base = "http://localhost:8000/v1"
        client = OpenAI(
            api_key=openai_api_key,
            base_url=openai_api_base,
        )
        # Convert image to base64
        image_data = encode_image(image_path)
        response = client.chat.completions.create(
            model="../SlideMaster/output/ppt2code_512_w_intro",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=4096,
            temperature=0
        )
        return response.choices[0].message.content
    
    except Exception as e:
        print(f"PPT2code call error: {str(e)}")
        if "longer than the maximum model length" in str(e):
            return "null"
        raise


@retry.retry(tries=5, delay=2)
def qwenvl_final_call(prompt, image_path2=None):
    try:
        openai_api_key = "EMPTY"
        openai_api_base = "http://localhost:8000/v1"
        client = OpenAI(
            api_key=openai_api_key,
            base_url=openai_api_base,
        )
        
        response = client.chat.completions.create(
            model="../SlideMaster/output/ppt2code_512_w_intro",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt}
                    ]
                }
            ],
            max_tokens=4096,
            temperature=0
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"ppt2code call error: {str(e)}")
        if "longer than the maximum model length" in str(e):
            return "null"
        raise

@retry.retry(tries=2, delay=2)
def gpt_call(prompt, image_path, image_path2=None):
    try:
        # Encode image to base64
        image_data = encode_image(image_path)
        response = openai_client.chat.completions.create(
            model="gpt-4o-2024-11-20",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=4096,
            temperature=0
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"GPT call error: {str(e)}")
        raise


@retry.retry(tries=2, delay=2)
def gpt_final_call(prompt, image_path2=None):
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-2024-11-20",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt}
                    ]
                }
            ],
            max_tokens=4096,
            temperature=0
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"GPT call error: {str(e)}")
        raise

