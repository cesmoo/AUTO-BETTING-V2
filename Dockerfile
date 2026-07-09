FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install chromium
RUN playwright install-deps chromium

COPY . .

# Web Service မဟုတ်သောကြောင့် Python file ကို တိုက်ရိုက် Run ပါမည်
CMD ["python", "main.py"]
