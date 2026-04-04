#!/bin/sh
# Entrypoint for repo-lord DinD container
# Starts dockerd + tmux + GrugAgent CAVEHTTPServer

# Load encrypted secrets if available
if [ -f /repo-lord/plugin/secrets/load-secrets.sh ]; then
    . /repo-lord/plugin/secrets/load-secrets.sh
fi

# Clone target repo if specified
if [ -n "$TARGET_REPO" ] && [ ! -d /repo/.git ]; then
    echo "Cloning $TARGET_REPO..."
    git clone "$TARGET_REPO" /repo || true
fi

SESSION="${TMUX_SESSION:-lord}"

# Start dockerd via dind's entrypoint in background
echo "Starting Docker daemon..."
dockerd-entrypoint.sh dockerd &

# Wait for docker to be ready
echo "Waiting for Docker daemon..."
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30; do
    if docker info > /dev/null 2>&1; then
        echo "Docker daemon ready."
        break
    fi
    sleep 1
done

if ! docker info > /dev/null 2>&1; then
    echo "ERROR: Docker daemon failed to start"
    exit 1
fi

# Start tmux session
echo "Starting tmux session: $SESSION"
tmux new-session -d -s "$SESSION" -c /repo

# Start GrugAgent CAVEHTTPServer in background
GRUG_PORT="${GRUG_PORT:-8081}"
PARENT_URL="${PARENT_URL:-http://host.docker.internal:8080}"

echo "Starting GrugAgent server on port $GRUG_PORT (parent: $PARENT_URL)..."
python3 /repo-lord/grug_server.py \
    --port "$GRUG_PORT" \
    --parent "$PARENT_URL" \
    > /var/log/grug_server.log 2>&1 &
GRUG_PID=$!
echo "GrugAgent server started (PID: $GRUG_PID)"

# Wait for grug server to be ready
for i in 1 2 3 4 5 6 7 8 9 10; do
    if curl -s "http://localhost:$GRUG_PORT/health" > /dev/null 2>&1; then
        echo "GrugAgent server ready!"
        break
    fi
    sleep 1
done

echo "Container ready."
echo "  tmux: docker exec -it <container> tmux attach -t $SESSION"
echo "  grug: http://localhost:$GRUG_PORT/health"

# Keep container alive
exec tail -f /dev/null
