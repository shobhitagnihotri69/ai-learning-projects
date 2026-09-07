import os
import getpass
from huggingface_hub import HfApi, login

print("\n🚀 Deploying World Model to Hugging Face Spaces 🚀\n")

# 1. Login
try:
    from huggingface_hub import whoami
    user = whoami()["name"]
    print(f"✅ Already logged in as: {user}")
except Exception:
    print("🔑 You need to log in to Hugging Face.")
    print("Get your WRITE token here: https://huggingface.co/settings/tokens")
    token = getpass.getpass("Enter your HF Token (it will be hidden): ")
    login(token)
    user = whoami()["name"]
    print(f"✅ Logged in successfully as: {user}")

api = HfApi()

# 2. Define Space Name
space_name = "world-model-from-scratch"
repo_id = f"{user}/{space_name}"

# 3. Create Space
print(f"\n📦 Creating Space: {repo_id}...")
try:
    api.create_repo(
        repo_id=repo_id,
        repo_type="space",
        space_sdk="gradio",
        private=False,
        exist_ok=True
    )
    print("✅ Space created or already exists!")
except Exception as e:
    print(f"❌ Error creating space: {e}")
    exit(1)

# 4. Upload Files
print("\n📤 Uploading files to Hugging Face... (this might take a minute)")

files_to_upload = [
    "app.py",
    "network_v.py",
    "network_m.py",
    "collect_dataset.py",
    "pong_env.py",
    "pong_wm.pt",
    "requirements.txt"
]

for file in files_to_upload:
    if os.path.exists(file):
        print(f"   -> Uploading {file}...")
        api.upload_file(
            path_or_fileobj=file,
            path_in_repo=file,
            repo_id=repo_id,
            repo_type="space"
        )
    else:
        print(f"   ⚠️ WARNING: {file} not found locally!")

print(f"\n🎉 ALL DONE! Your model is live!")
print(f"🌍 View it here: https://huggingface.co/spaces/{repo_id}")
