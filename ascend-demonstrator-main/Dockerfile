FROM python:3.10

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory
WORKDIR /opt/WP-1-4

# Install system dependencies for GDAL
RUN apt-get update && \
    apt-get install -y \
    gdal-bin \
    libgdal-dev \
    ffmpeg \
    libsm6 \
    libxext6  -y


# Copy the requirements file and install Python dependencies
COPY requirements.txt /opt/WP-1-4/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy the rest of the application code
COPY . /opt/WP-1-4/
