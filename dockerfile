# Use an official Python runtime as the base image
FROM python:3.13-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install the dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables
# Set the FLASK_APP environment variable (ensure your app's entry point file is named 'main.py' or change accordingly)
ENV FLASK_APP=main.py
ENV FLASK_ENV=production  
# Expose the port the app will run on
EXPOSE 5000

# Run the Flask app using `flask run`
CMD ["flask", "run", "--host=0.0.0.0"]