FROM python:3.11-slim

# Set working dir early so all subsequent commands are relative to it
WORKDIR /app

# Copy only requirements first — Docker caches this layer until requirements.txt
# changes, so code edits don't trigger a full pip install.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
