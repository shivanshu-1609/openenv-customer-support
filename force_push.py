from huggingface_hub import HfApi
import os

print("Forcing direct API upload to Hugging Face Spaces...")
api = HfApi()
try:
    # We upload the current folder ignoring the large venv directory
    api.upload_folder(
        folder_path=".",
        repo_id="shivanshu1609/customer-support-env",
        repo_type="space",
        ignore_patterns=["venv/**", "venv", ".git/**", ".git", "__pycache__/**", "*.pyc"]
    )
    print("Files uploaded successfully! Check your Hugging Face space.")
except Exception as e:
    print(f"Error occurred during upload: {e}")
