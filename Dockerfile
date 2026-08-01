FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Expose backend REST API port
EXPOSE 5000

# Start Flask backend server
CMD ["python", "api.py"]
