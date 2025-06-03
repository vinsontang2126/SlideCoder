import time
from utils import *
import os
import retry
# import anthropic
from openai import OpenAI
import base64
import requests
import json
import random
from vllm import LLM, SamplingParams
import PIL

openai_client = OpenAI(
                api_key="",
                base_url="https://openkey.cloud/v1")

# 通义千问配置
QWEN_API_KEY = ""
QWEN_HOST = "https://dashscope.aliyuncs.com/compatible-mode/v1"

def qwen_headers():
    return {
        "Authorization": f"Bearer {QWEN_API_KEY}",
        "Content-Type": "application/json",
        "X-DashScope-Plugin": "plugin_name"  # 如果需要使用插件可以设置
    }

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
            model="../../output/ppt2code_512_wo_intro",
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
            model="../../output/ppt2code_512_wo_intro",
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

@retry.retry(tries=2, delay=2)
def claude_call(prompt, image_path, image_path2=None):
    try:
        # Use encode_image for consistency
        image_data = encode_image(image_path)
        message = claude.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=4096,
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_data
                            }
                        }
                    ]
                }
            ]
        )
        return message.content[0].text
    except Exception as e:
        print(f"Claude call error: {str(e)}")
        raise


@retry.retry(tries=2, delay=2)
def qwen_call(prompt, image_path):
    try:
        # Convert image to base64
        image_data = encode_image(image_path)
        client = OpenAI(
            api_key=QWEN_API_KEY,
            base_url=QWEN_HOST
        )
        
        response = client.chat.completions.create(
            model="qwen2.5-72b-instruct",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                ]
            }]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Qwen call error: {str(e)}")
        raise


@retry.retry(tries=2, delay=2)
def gemini_feedback_call(prompt, image_path1, image_path2):
    try:
        model = genai.GenerativeModel('gemini-1.5-pro')
        # Convert both images to base64
        image_data1 = encode_image(image_path1)
        image_data2 = encode_image(image_path2)
        
        response = model.generate_content(
            contents=[
                prompt,
                {
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": image_data1
                    }
                },
                {
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": image_data2
                    }
                }
            ],
            generation_config=genai.types.GenerationConfig(
                temperature=0,
                max_output_tokens=4096,
            )
        )
        return response.text
    except Exception as e:
        print(f"Gemini feedback call error: {str(e)}")
        raise

@retry.retry(tries=2, delay=2)
def gpt_feedback_call(prompt, image_path1, image_path2):
    try:
        # Use encode_image for both images
        image_data1 = encode_image(image_path1)
        image_data2 = encode_image(image_path2)
        
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_data1}"}
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_data2}"}
                        }
                    ]
                }
            ],
            max_tokens=4096,
            temperature=0
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"GPT feedback call error: {str(e)}")
        raise

@retry.retry(tries=2, delay=2)
def claude_feedback_call(prompt, image_path1, image_path2):
    try:
        # Use encode_image for both images
        image_data1 = encode_image(image_path1)
        image_data2 = encode_image(image_path2)
            
        message = claude.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=4096,
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_data1
                            }
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_data2
                            }
                        }
                    ]
                }
            ]
        )
        return message.content[0].text
    except Exception as e:
        print(f"Claude feedback call error: {str(e)}")
        raise


@retry.retry(tries=2, delay=2)
def qwen_feedback_call(prompt, image_path1, image_path2):
    try:
        # Convert images to base64
        image_data1 = encode_image(image_path1)
        image_data2 = encode_image(image_path2)
        
        client = OpenAI(
            api_key=QWEN_API_KEY,
            base_url=QWEN_HOST
        )
        
        response = client.chat.completions.create(
            model="qwen2.5-72b-instruct",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data1}"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data2}"}}
                ]
            }]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Qwen feedback call error: {str(e)}")
        raise

# Llama配置
LLAMA_API_KEY = ""
LLAMA_HOST = "https://api.groq.com/openai/v1"

@retry.retry(tries=2, delay=2)
def llama_call(prompt, image_path):
    try:
        # Convert image to base64
        image_data = encode_image(image_path)
        
        headers = {
            "Authorization": f"Bearer {LLAMA_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.2-90b-vision-preview",
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                ]
            }],
            "temperature": 0,
            "max_tokens": 4096
        }
        
        response = requests.post(
            f"{LLAMA_HOST}/chat/completions",
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            print(f"Llama API error: {response.status_code}")
            print(f"Response: {response.text}")
            raise Exception(f"Llama API call failed with status code: {response.status_code}")
            
    except Exception as e:
        print(f"Llama call error: {str(e)}")
        raise

@retry.retry(tries=2, delay=2)
def llama_feedback_call(prompt, image_path1, image_path2):
    try:
        # Convert images to base64
        image_data1 = encode_image(image_path1)
        image_data2 = encode_image(image_path2)
        
        headers = {
            "Authorization": f"Bearer {LLAMA_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.2-90b-vision-preview",
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data1}"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data2}"}}
                ]
            }],
            "temperature": 0,
            "max_tokens": 4096
        }
        
        response = requests.post(
            f"{LLAMA_HOST}/chat/completions",
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            print(f"Llama API error: {response.status_code}")
            print(f"Response: {response.text}")
            raise Exception(f"Llama API call failed with status code: {response.status_code}")
            
    except Exception as e:
        print(f"Llama feedback call error: {str(e)}")
        raise

# DeepSeek配置
DEEPSEEK_API_KEY = ""
DEEPSEEK_HOST = "https://api.deepseek.com"

@retry.retry(tries=2, delay=2)
def deepseek_call(prompt, image_path):
    try:
        # Convert image to base64
        image_data = encode_image(image_path)
        
        client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_HOST
        )
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates Python code for PowerPoint slides."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                    ]
                }
            ],
            temperature=0,
            max_tokens=4096,
            stream=False
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"DeepSeek call error: {str(e)}")
        raise

@retry.retry(tries=2, delay=2)
def deepseek_feedback_call(prompt, image_path1, image_path2):
    try:
        # Convert images to base64
        image_data1 = encode_image(image_path1)
        image_data2 = encode_image(image_path2)
        
        client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_HOST
        )
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates Python code for PowerPoint slides."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data1}"}},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data2}"}}
                    ]
                }
            ],
            temperature=0,
            max_tokens=4096,
            stream=False
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"DeepSeek feedback call error: {str(e)}")
        raise

