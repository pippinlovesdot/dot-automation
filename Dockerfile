FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create assets directory if not exists
RUN mkdir -p assets

# Expose port (set via PORT env var)
EXPOSE 8080

# Run the application
CMD ["python", "main.py"]
