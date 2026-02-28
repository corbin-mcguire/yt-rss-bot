FROM python:3.11-slim

# Create a non-root user
RUN useradd -m -u 1000 botuser

WORKDIR /app

# Install dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY bot.py poller.py db.py ./

# Data directory for the SQLite database (mounted as a volume)
RUN mkdir /data && chown botuser:botuser /data

USER botuser

CMD ["python", "bot.py"]
