# Playwright မှ တရားဝင် ထုတ်ထားသော Ubuntu Jammy (Python) Base Image ကို အသုံးပြုခြင်း
FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

# Working Directory သတ်မှတ်ခြင်း
WORKDIR /app

# Requirements များ Copy ကူးပြီး Install လုပ်ခြင်း
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Official image တွင် dependencies များ ပါဝင်ပြီးဖြစ်၍ install-deps လုပ်ရန် မလိုတော့ပါ
# Chromium ကိုသာ သေချာစေရန် ထပ်မံသွင်းပါမည်
RUN playwright install chromium

# ကျန်ရှိသော Code များကို Copy ကူးခြင်း
COPY . .

# Bot ကို စတင် Run မည်
CMD ["python", "main.py"]
