FROM python:3.10.16

WORKDIR /app

# Copy requirements trước để tận dụng cache
COPY requirements.txt .

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        python3-dev \
        libgl1 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir numpy==1.23.5 Cython==3.0.11
# Giảm tối đa dung lượng
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir tensorflow==2.13.0 \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY src app
COPY .env .env
RUN pip uninstall numpy -y
RUN pip install numpy==1.23.5
ENV TZ=Asia/Ho_Chi_Minh
ENV PYTHONPATH=/app/
