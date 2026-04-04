# Repo Lord - DinD (Docker in Docker)
# GrugAgent container — code execution worker for Observatory
# Runs CAVEHTTPServer on port 8081, registers with parent sancrev

FROM docker:dind

# Install dependencies
RUN apk add --no-cache \
    bash \
    git \
    jq \
    curl \
    tmux \
    nodejs \
    npm \
    openssh \
    python3 \
    py3-pip \
    python3-dev \
    gcc \
    musl-dev

# Install Claude CLI
RUN npm install -g @anthropic-ai/claude-code

# Install age for secret encryption
RUN apk add --no-cache age

# Create working directories
WORKDIR /repo-lord
RUN mkdir -p /repo /root/.claude /state

# Pin Python deps to exact versions matching mind_of_god BEFORE package installs
RUN pip3 install --break-system-packages \
    'langgraph==0.2.60' \
    'langchain-core==0.3.83' \
    'langchain==0.3.27' \
    'langchain-anthropic==0.3.22' \
    'langchain-google-genai==2.1.12' \
    'langchain-openai==0.3.35' \
    'langchain-community==0.3.21' \
    'langgraph-checkpoint==2.0.10' \
    'langgraph-prebuilt==0.1.7' \
    'anthropic==0.84.0' \
    'beartype==0.15.0' \
    'fastapi==0.135.1' \
    'uvicorn==0.41.0' \
    'httpx==0.28.1' \
    'pydantic==2.12.5'

# Copy and install local packages (order matters: deps first)
COPY llegos/ /repo-lord/llegos/
RUN cd /repo-lord/llegos && pip3 install --break-system-packages . || true

COPY sdna/ /repo-lord/sdna/
RUN cd /repo-lord/sdna && pip3 install --break-system-packages . || true

COPY cave-harness/ /repo-lord/cave-harness/
RUN cd /repo-lord/cave-harness && pip3 install --break-system-packages . || true

COPY heaven-framework/ /repo-lord/heaven-framework/
RUN cd /repo-lord/heaven-framework && pip3 install --break-system-packages . || true

# Docker SDK needed by heaven_base.tool_utils.hermes_utils
RUN pip3 install --break-system-packages docker || true

# Copy grug agent + server
COPY grug_agent.py /repo-lord/grug_agent.py
COPY grug_server.py /repo-lord/grug_server.py

# No remote/ scripts needed — CAVEHTTPServer replaces the old bridge

# Expose GrugAgent CAVEHTTPServer port
EXPOSE 8081

# Entrypoint starts dockerd + tmux + grug server
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]
