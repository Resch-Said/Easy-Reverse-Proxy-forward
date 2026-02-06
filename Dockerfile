FROM python:3.11-slim

# Install iptables and required system packages including build dependencies
RUN apt-get update && \
    apt-get install -y \
    iptables \
    iproute2 \
    procps \
    gcc \
    python3-dev && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt

# Copy application files
COPY portfw_GUI.py /app/
COPY templates/ /app/templates/

# Create volume mount point for persistent rules
VOLUME ["/app/data"]

# Expose Flask port
EXPOSE 5000

# Run the application
CMD ["python3", "portfw_GUI.py"]
