import os
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()
azure_key = os.getenv("AZURE_SPEECH_KEY")
region = os.getenv("AZURE_SPEECH_REGION", "eastus")

print(f"Region: {region}")
print(f"Key (first 10 chars): {azure_key[:10]}...")
print(f"Key length: {len(azure_key)}")

# Method 1: Direct subscription key
print("\n--- Method 1: Direct Ocp-Apim-Subscription-Key ---")
url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
headers = {
    "Ocp-Apim-Subscription-Key": azure_key,
    "Content-Type": "application/ssml+xml",
    "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3",
    "User-Agent": "CallIQ"
}
ssml = "<speak version='1.0' xml:lang='en-US'><voice xml:lang='en-US' xml:gender='Female' name='en-US-JennyNeural'>Hello</voice></speak>"

async def run():
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(url, headers=headers, content=ssml.encode("utf-8"))
        print(f"Status: {r.status_code}")
        print(f"Headers: {dict(r.headers)}")
        if r.status_code != 200:
            print(f"Error body: {r.text}")
        else:
            print(f"Audio bytes received: {len(r.content)}")

        # Method 2: Token-based auth
        print("\n--- Method 2: Fetch token first ---")
        token_url = f"https://{region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
        token_r = await client.post(token_url, headers={"Ocp-Apim-Subscription-Key": azure_key}, content=b"")
        print(f"Token status: {token_r.status_code}")
        if token_r.status_code == 200:
            token = token_r.text
            print(f"Token (first 20): {token[:20]}...")
            headers2 = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3",
                "User-Agent": "CallIQ"
            }
            r2 = await client.post(url, headers=headers2, content=ssml.encode("utf-8"))
            print(f"TTS with token status: {r2.status_code}")
            if r2.status_code == 200:
                print(f"Audio bytes received: {len(r2.content)}")
            else:
                print(f"Error: {r2.text}")
        else:
            print(f"Token error: {token_r.text}")

asyncio.run(run())
