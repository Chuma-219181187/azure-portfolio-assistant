# app.py
from flask import Flask, request, jsonify, render_template
import os
import requests
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

app = Flask(__name__)

# Initialize Azure Key Vault client
key_vault_name = os.getenv("AZURE_KEY_VAULT_NAME")
key_vault_url = f"https://{key_vault_name}.vault.azure.net"

def get_secret(secret_name):
    try:
        credential = DefaultAzureCredential()
        client = SecretClient(vault_url=key_vault_url, credential=credential)
        retrieved_secret = client.get_secret(secret_name)
        return retrieved_secret.value
    except Exception as e:
        print(f"Key Vault error: {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask_assistant():
    user_message = request.json.get('message')
    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    try:
        # Try to use Azure OpenAI first
        azure_openai_key = get_secret("azure-openai-key")
        azure_openai_endpoint = get_secret("azure-openai-endpoint")
        
        if azure_openai_key and azure_openai_endpoint:
            # Use Azure OpenAI
            headers = {
                "Content-Type": "application/json",
                "api-key": azure_openai_key
            }
            data = {
                "messages": [{"role": "user", "content": user_message}],
                "max_tokens": 150
            }
            # Azure OpenAI uses a different endpoint structure
            deployment_name = "gpt-35-turbo"  # Your deployment name
            endpoint = f"{azure_openai_endpoint}/openai/deployments/{deployment_name}/chat/completions?api-version=2023-12-01-preview"
            response = requests.post(endpoint, headers=headers, json=data)
        else:
            # Fallback to standard OpenAI
            openai_key = get_secret("openai-api-key") or os.getenv("OPENAI_API_KEY")
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {openai_key}"
            }
            data = {
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": user_message}],
                "max_tokens": 150
            }
            endpoint = "https://api.openai.com/v1/chat/completions"
            response = requests.post(endpoint, headers=headers, json=data)

        response.raise_for_status()
        result = response.json()
        
        # Handle both Azure and OpenAI response formats
        if 'choices' in result:
            answer = result['choices'][0]['message']['content']
        else:
            answer = result['choices'][0]['message']['content']  # Azure format
        
        return jsonify({"response": answer})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "service": "Azure Portfolio Assistant"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)