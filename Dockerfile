FROM python:3.11-slim-bookworm

# Set environment variables
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy dependencies first for efficient caching
COPY requirements.txt .

# Install LaTeX, dvisvgm, inkscape, and python packages
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        texlive-latex-base \
        texlive-fonts-recommended \
        texlive-extra-utils \
        texlive-latex-extra \
        texlive-science \
        dvisvgm \
        inkscape && \
    rm -rf /var/lib/apt/lists/* && \
    pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . /app

# Expose port 8080 (standard for Cloud Run)
EXPOSE 8080

# Command to run gunicorn serving Flask app on port 8080
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
