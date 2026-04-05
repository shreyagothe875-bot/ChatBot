from google import genai

API_KEY = "AIzaSyDVdRMc5p_haACS95fALCypijE2Ov8_-ys"
client = genai.Client(api_key=API_KEY)

print("Models available to this key:")
try:
    for model in client.models.list():
        # Only print models that support text generation
        if 'generateContent' in model.supported_actions:
            print(f"- {model.name}")
except Exception as e:
    print(f"Error: {e}")