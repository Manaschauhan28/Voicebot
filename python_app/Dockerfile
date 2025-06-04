# Use Python 3.9.0 as base image
FROM python:3.9.0

# Set the working directory inside the container
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set AWS Credentials as Environment Variables
ENV AWS_ACCESS_KEY_ID=AKIAVRUVV6PBED2P6E7I
ENV AWS_SECRET_ACCESS_KEY=DL4f4GfhTIjh8sybaT7ejhzBaAP5uR0ZtctcqsR4
ENV AWS_DEFAULT_REGION=us-east-1

# Copy the rest of the application files
COPY . .

# Expose port (if your app runs on a specific port, e.g., Flask default 5000)
EXPOSE 8000

# Set the default command to run the application
CMD ["python", "app.py"]
