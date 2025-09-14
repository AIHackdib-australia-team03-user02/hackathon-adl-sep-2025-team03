# Use official Python 3.12 image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy requirements and source code
COPY requirements.txt ./
COPY . ./

# Install dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Set environment variables (if using .env)
# COPY .env .env

# Default command to run your main script

# Expose FastAPI/Uvicorn port
EXPOSE 8000

# Default command to run your main script
CMD ["python", "webserver_ajax.py"]


# > docker build -t hackathon-adl-sep-2025-team03 . 
# > docker run -p 8000:8000 --rm -it hackathon-adl-sep-2025-team03