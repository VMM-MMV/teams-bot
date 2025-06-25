from agent.utils.io_manager import read_files
import json
from pathlib import Path

DIR_PATH = Path("/home/serveruser/mcp-sse/procedures")
METADATA_NAME = "procedures_metadata"
METADATA_DIR = DIR_PATH / f"{METADATA_NAME}.json"

def get_procedures_metadata():
    with METADATA_DIR.open("r") as f:
        return json.load(f)

def yield_procedures(dir_path, allowed_files=[]):
    for name, file_contents in read_files(dir_path, allowed_files=allowed_files):
        if name == METADATA_NAME: continue
        yield f"<document name={name}>{file_contents}</document>\n"

def load_procedures(dir, allowed_files=[]):
    dir = Path(dir)
    return "".join(yield_procedures(dir, allowed_files=allowed_files))

if __name__ == "__main__":
    res = load_procedures(DIR_PATH)
    print(res)