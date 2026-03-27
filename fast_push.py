from huggingface_hub import HfApi
import os

api = HfApi()
repo_id = "shivanshu1609/customer-support-env"

files_to_upload = [
    "README.md",
    "openenv.yaml",
    "models.py",
    "client.py",
    "baseline.py",
    "gemini_baseline.py",
    "requirements.txt",
    "server/Dockerfile",
    "server/app.py",
    "server/requirements.txt",
    "server/__init__.py",
    "server/support_env_environment.py"
]

print("Fast push starting...")
for f in files_to_upload:
    if os.path.exists(f):
        print(f"Uploading {f}...")
        try:
            api.upload_file(
                path_or_fileobj=f,
                path_in_repo=f,
                repo_id=repo_id,
                repo_type="space"
            )
        except Exception as e:
            print(f"Failed {f}: {e}")
    else:
        print(f"File {f} not found locally.")

print("Fast push complete!")
