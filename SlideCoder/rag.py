
import os
import numpy as np
import openai
import random
import requests
import time
from requests.exceptions import ConnectionError


def get_embedding(prompt, client):
    for _ in range(10):
        api_key = ""
        url = "https://api.siliconflow.cn/v1/embeddings"
        payload = {
            "model": "BAAI/bge-m3",
            "input": prompt,
            "encoding_format": "float"
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        for attempt in range(10):
            try:
                response = requests.request("POST", url, json=payload, headers=headers, timeout=30)
                break
            except ConnectionError as e:
                print(f"Attempt {attempt + 1} Failed: {e}")
                time.sleep(2)
        if response.status_code == 200:
            data = response.json()
            embedding = data['data'][0]['embedding']
            return embedding
        else:
            print("Reconnect----")

    print(f"Request failed, status code:{response.status_code}")

def load_data(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        if file_path.find("library")!=-1:
            statements = [block.strip().replace('    ', '\t') for block in content.split('\n\n\n') if block.strip()]
        else:
            statements = [block.strip() for block in content.split('########') if block.strip()]
        return statements
    
    except FileNotFoundError:
        print(f"file not found: {file_path}")
        return []
    except UnicodeDecodeError:
        print(f"File encoding error: {file_path}")
        return []

def generate_embeddings(statements, client):
    embeddings = []
    for statement in statements:
        embedding = get_embedding(statement, client)
        if embedding is not None:
            embeddings.append(embedding)
    return np.array(embeddings)

def search_similar_statements(query, statements, embeddings, client, n=3):
    query_embedding = get_embedding(query, client)
    if query_embedding is None:
        return []
    # Calculate cosine similarity using vectorized operations
    similarities = np.dot(embeddings, query_embedding) / (
        np.linalg.norm(embeddings, axis=1) * np.linalg.norm(query_embedding)
    )
    top_indices = np.argsort(similarities)[::-1][:n]
    results = [(statements[i], similarities[i]) for i in top_indices]
    return results

def rag_main(txt_file_path, query, n=3):
    statements = load_data(txt_file_path)
    if not statements:
        return []
    
    embeddings = generate_embeddings(statements, client)
    if embeddings.size == 0:
        return []
    
    results = search_similar_statements(query, statements, embeddings, client, n=n)
    return results

def query_db(query, txt_file_path, n=3):
    results = rag_main(txt_file_path, query, n)
    rag_result=""
    for i, (statement, similarity) in enumerate(results, 1):
        rag_result = rag_result+statement+"\n"

    return rag_result

if __name__ == "__main__":
    txt_file_path = "./db/library.py"
    query = "What is the use of API?"
    results = rag_main(txt_file_path, query, n=3)
    for i, (statement, similarity) in enumerate(results, 1):
        print(type(statement))
        print(statement)