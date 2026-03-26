FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY config.py trader.py screener.py ./
COPY data/ data/
COPY strategies/ strategies/
COPY execution/ execution/
COPY risk/ risk/
COPY monitoring/ monitoring/
COPY astro/ astro/

# Create logs directory
RUN mkdir -p logs

# Set timezone for IST market hours
ENV TZ=Asia/Kolkata

# Default: auto mode (ask paper/live on Telegram, trade all day)
CMD ["python", "trader.py"]
