# Use the official Python 3.10 image as the base image
FROM python:3.10

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements.txt file into the container
COPY requirements.txt .

# Install the required system dependencies for LDAP and SSL support
RUN apt-get update && apt-get install -y libldap2-dev libsasl2-dev libssl-dev

# Install app dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire app directory into the container
COPY . .

# Move the 'data' folder to the appropriate location inside the container
RUN mv ./app/data /app/data

# Expose the port that your Flask app will run on (change the port if needed)
EXPOSE 5000

# Copy the loop.sh script into the container
COPY loop.sh /app/loop.sh

# Make the script executable inside the container
RUN chmod +x /app/loop.sh

# Command to run the Flask app using Gunicorn and the loop.sh script
CMD ["bash", "-c", "gunicorn app.main:app --bind 0.0.0.0:5000 & /app/loop.sh"]
