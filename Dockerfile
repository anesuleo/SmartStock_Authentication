# ── Stage 1: Builder ──────────────────────────────────────────────────────────
# Install dependencies and build wheels in a separate stage so the final
# image doesn't need build tools, keeping it small and secure.
FROM python:3.11-slim AS builder

WORKDIR /app

# Upgrade pip and install wheel for building packages
RUN pip install --upgrade pip wheel

# Copy requirements and build wheels
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt


# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
# Copy only the pre-built wheels from the builder stage — no build tools needed
FROM python:3.11-slim AS runtime

WORKDIR /app

# Create a non-root user for security
# Running as root inside a container is a security risk
RUN useradd -m appuser

# Install the pre-built wheels from the builder stage
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Copy application source code
COPY . .

# Give the non-root user ownership of the app files
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

EXPOSE 8000

# Start the FastAPI app with uvicorn
CMD ["uvicorn", "app.main:app", "--host=0.0.0.0", "--port=8000"]