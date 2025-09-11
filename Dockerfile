# Use official Python 3.12 image
FROM alpine:3.16

# Set working directory
WORKDIR /app

# Copy requirements and source code
COPY requirements.txt ./
COPY . ./

RUN apk add libgomp
RUN apk add python3
RUN apk add py3-pip
RUN apk add --virtual build-dependencies build-base gcc wget git pkgconfig
RUN apk add meson

# Install dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Set environment variables (if using .env)
COPY .env .env

# Default command to run your main script
CMD ["python", "main.py"]


# > docker build -t hackathon-adl-sep-2025-team03 . 
# > docker run --rm -it hackathon-adl-sep-2025-team03
