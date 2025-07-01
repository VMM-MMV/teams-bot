import os
from dotenv import load_dotenv

def get_env(env_name, default=None):
    load_dotenv()
    return os.environ.get(env_name, default)

def list_files(dir_path):
    for root, dirs, files in os.walk(dir_path):
        for file in files:
            yield os.path.join(root, file)
    
def read_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()
    
def list_files(dir_path):
    for root, dirs, files in os.walk(dir_path):
        for file in files:
            yield os.path.join(root, file)

def read_files(dir_path, allowed_files=[], ignored_files=[]):
    for file_path in list_files(dir_path):
        file_name = os.path.basename(file_path).rsplit(".", 1)[0]
        if allowed_files and file_name not in allowed_files: continue
        if file_name in ignored_files: continue
        
        yield file_name, read_file(file_path)