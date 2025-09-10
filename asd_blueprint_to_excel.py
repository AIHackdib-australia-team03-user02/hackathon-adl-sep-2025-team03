import os
import glob
import pandas as pd
from dotenv import load_dotenv
from openai import AzureOpenAI
import re
from sqlalchemy import text
import tiktoken

load_dotenv()

# Use the local folder directly
LOCAL_DIR = "ASD-Blueprint-for-Secure-Cloud-main"

# Find all txt, pdf, md, docx files
file_types = ["docx", "md", "txt"]
all_files = []
for ext in file_types:
    all_files.extend(glob.glob(f"{LOCAL_DIR}/**/*.{ext}", recursive=True))

# Azure OpenAI embedding setup
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_EMBEDDING_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_EMBEDDING_API_VERSION"),
)
DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
'''
def chunk_text(text, max_tokens=500):
    # Simple chunking by paragraphs
    paras = text.split('\n\n')
    chunks = []
    current = ""
    for para in paras:
        if len(current) + len(para) < max_tokens * 4:  # rough char/token estimate
            current += para + "\n\n"
        else:
            chunks.append(current)
            current = para + "\n\n"
    if current:
        chunks.append(current)
    return chunks

def chunk_text(text, max_tokens=2000):
    # Use tiktoken to count tokens accurately
    enc = tiktoken.encoding_for_model("text-embedding-ada-002")  # or your model
    paras = text.split('\n\n')
    chunks = []
    current = ""
    for para in paras:
        test_chunk = current + para + "\n\n"
        if len(enc.encode(test_chunk)) < max_tokens:
            current = test_chunk
        else:
            if current:
                chunks.append(current)
            # If paragraph itself is too big, split it
            if len(enc.encode(para)) > max_tokens:
                words = para.split()
                sub_chunk = ""
                for word in words:
                    test_sub = sub_chunk + word + " "
                    if len(enc.encode(test_sub)) < max_tokens:
                        sub_chunk = test_sub
                    else:
                        chunks.append(sub_chunk)
                        sub_chunk = word + " "
                if sub_chunk:
                    chunks.append(sub_chunk)
                current = ""
            else:
                current = para + "\n\n"
    if current:
        chunks.append(current)
    return chunks
'''
text_md_erros = 0
pdf_errors = 0
docx_errors = 0

def chunk_text(text, max_tokens=2000, splitter=None):
    enc = tiktoken.encoding_for_model("text-embedding-3-large")
    if splitter:
        paras = splitter(text)
    else:
        paras = re.split(r'\n\s*\n', text)
    chunks = []
    current = ""
    for para in paras:
        para = para.strip()
        if not para:
            continue
        test_chunk = current + (para + "\n\n" if current else para + "\n\n")
        if len(enc.encode(test_chunk)) < max_tokens:
            current = test_chunk
        else:
            if current:
                chunks.append(current.strip())
            # If paragraph itself is too big, split by sentences
            if len(enc.encode(para)) > max_tokens:
                sentences = re.split(r'(?<=[.!?])\s+', para)
                sub_chunk = ""
                for sent in sentences:
                    test_sub = sub_chunk + (sent + " " if sub_chunk else sent + " ")
                    if len(enc.encode(test_sub)) < max_tokens:
                        sub_chunk = test_sub
                    else:
                        if sub_chunk:
                            chunks.append(sub_chunk.strip())
                        sub_chunk = sent + " "
                if sub_chunk:
                    chunks.append(sub_chunk.strip())
                current = ""
            else:
                current = para + "\n\n"
    if current:
        chunks.append(current.strip())
    return chunks

# Helper functions for reading different file types
def read_txt_md(file):
    try:
        with open(file, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(file, "r", encoding="latin-1") as f:
                return f.read()
        except Exception as e:
            text_md_erros += 1
            print(f"Could not read TXT/MD {file}: {e}")
            return ""

def read_pdf(file):
    try:
        import PyPDF2
        with open(file, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
        return text
    except Exception as e:
        pdf_errors += 1
        print(f"Could not read PDF {file}: {e}")
        return ""

def read_docx(file):
    try:
        import docx
        doc = docx.Document(file)
        text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
        return text
    except Exception as e:
        docx_errors += 1
        print(f"Could not read DOCX {file}: {e}")
        return ""
    
def is_valid_chunk(chunk):
    # Must be a string, not empty, and contain at least some alphanumeric characters
    if not isinstance(chunk, str):
        return False
    chunk = chunk.strip()
    if not chunk:
        return False
    # Remove YAML frontmatter if present
    if chunk.startswith("---"):
        chunk = re.sub(r"^---.*?---\s*", "", chunk, flags=re.DOTALL)
    # Must contain at least 3 letters or numbers
    if len(re.findall(r"[a-zA-Z0-9]", chunk)) < 3:
        return False
    return True

def preprocess_txt(text):
    # Remove excessive whitespace: replace multiple spaces/newlines with a single newline
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{2,}', '\n', text)
    return text.strip()

def curly_brace_splitter(text):
    # Split at each closing curly brace, keeping the brace
    parts = re.split(r'(\})', text)
    chunks = []
    current = ""
    for part in parts:
        current += part
        if part == "}":
            chunks.append(current.strip())
            current = ""
    if current.strip():
        chunks.append(current.strip())
    return chunks

#rows = []
print("Total files found:", len(all_files))


#output_file = "asd_blueprint_with_embeddings.csv"
output_file = "blueprint_embeddings.csv"

'''
first_write = not os.path.exists(output_file)
count_errors = 0

for file_number, file in enumerate(all_files, 1):
    print(f"[{file_number}/{len(all_files)}] File: {file}")
    ext = file.split(".")[-1].lower()
    splitter = None
    if ext in ["md", "txt"]:
        text = read_txt_md(file)
        if ext == "txt":
            print("Length before preprocess", len(text))
            text = preprocess_txt(text)
            print("Length after preprocess", len(text))
            splitter = curly_brace_splitter
    elif ext == "pdf":
        text = read_pdf(file)
    elif ext == "docx":
        text = read_docx(file)
    else:
        continue
    
    if not text or not isinstance(text, str):
        continue

    chunks = chunk_text(text, splitter=splitter)
    print(f"{file}: {len(chunks)} chunks")
    for chunk in chunks:
        print(chunk)
        if not is_valid_chunk(chunk):
            continue
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            print("Length", len(chunk))
            embedding = client.embeddings.create(
                input=chunk,
                model=DEPLOYMENT
                ).data[0].embedding
            row = {
                "file": file,
#                "chunk": chunk,
                "embedding": str(embedding)
                }
            df = pd.DataFrame([row])
            df.to_csv(output_file, mode='a', header=first_write, index=False)
            first_write = False
        except Exception as e:
            count_errors += 1
            print(f"Failed to embed chunk from {file}: {e}")
'''

enc = tiktoken.encoding_for_model("text-embedding-3-large")
max_tokens = 8100

def embed_and_save(chunk, file, enc, max_tokens, client, DEPLOYMENT, output_file, first_write, count_errors):
    tokens = enc.encode(chunk)
    while len(tokens) > max_tokens:
        print(f"Chunk too large ({len(tokens)} tokens), splitting further")
        count_errors += 1
        part = enc.decode(tokens[:max_tokens])
        embedding = client.embeddings.create(
            input=part,
            model=DEPLOYMENT
        ).data[0].embedding
        row = {
            "file": file,
            "embedding": str(embedding)
        }
        df = pd.DataFrame([row])
        df.to_csv(output_file, mode='a', header=first_write[0], index=False)
        first_write[0] = False
        tokens = tokens[max_tokens:]
    if tokens:
        part = enc.decode(tokens)
        embedding = client.embeddings.create(
            input=part,
            model=DEPLOYMENT
        ).data[0].embedding
        row = {
            "file": file,
            "embedding": str(embedding)
        }
        df = pd.DataFrame([row])
        df.to_csv(output_file, mode='a', header=first_write[0], index=False)
        first_write[0] = False
first_write = [not os.path.exists(output_file)]
count_errors = 0
for file_number, file in enumerate(all_files, 1):
    print(f"[{file_number}/{len(all_files)}] File: {file}")
    ext = file.split(".")[-1].lower()
    splitter = None
    if ext in ["md", "txt"]:
        text = read_txt_md(file)
        if ext == "txt":
            print("Length before preprocess", len(text))
            text = preprocess_txt(text)
            print("Length after preprocess", len(text))
            splitter = curly_brace_splitter
    elif ext == "pdf":
        text = read_pdf(file)
    elif ext == "docx":
        text = read_docx(file)
    else:
        continue
    
    if not text or not isinstance(text, str):
        continue

    chunks = chunk_text(text, splitter=splitter)
    print(f"{file}: {len(chunks)} chunks")

    # Usage in your loop:
    for chunk in chunks:
        if not is_valid_chunk(chunk):
            continue
        chunk = chunk.strip()
        if not chunk:
            continue
        embed_and_save(chunk, file, enc, max_tokens, client, DEPLOYMENT, output_file, first_write, count_errors)

print(f"Total embedding errors: {count_errors}")
print(f"Total MD errors: {text_md_erros}")
print(f"Total PDF errors: {pdf_errors}")
print(f"Total DOCX errors: {docx_errors}")

'''


# Convert embeddings to string for Excel
df = pd.DataFrame(rows)
df["embedding"] = df["embedding"].apply(lambda x: str(x))
df.to_excel("asd_blueprint_with_embeddings.xlsx", index=False)

print(f"Saved {len(rows)} chunks with embeddings to asd_blueprint_with_embeddings.xlsx")
'''