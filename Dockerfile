FROM python:3.8

# Set the working directory
WORKDIR /app

# Copy the requirements file and install the dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the source code
COPY . .

RUN mkdir /app/downloads

# Run the bot
CMD ["python", "bot.py"]
