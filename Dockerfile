# ==========================================
# STAGE 1: Build the React (Vite) Frontend
# ==========================================
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

# Accept the Clerk publishable key as a build argument
ARG VITE_CLERK_PUBLISHABLE_KEY
ENV VITE_CLERK_PUBLISHABLE_KEY=$VITE_CLERK_PUBLISHABLE_KEY

# Install dependencies first (optimizes Docker caching)
COPY frontend/package*.json ./
RUN npm ci

# Copy the rest of the frontend code and build it
COPY frontend/ .
RUN npm run build

# ==========================================
# STAGE 2: Build the FastAPI Backend
# ==========================================
FROM python:3.11-slim
WORKDIR /app

# Prevent Python from writing .pyc files and buffer stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install backend dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all backend code (main.py, tools, graph, data, etc.)
COPY . .

# Copy the compiled frontend assets from Stage 1 into the directory main.py expects
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Expose the port that Uvicorn runs on
EXPOSE 8000

# Start the FastAPI application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]