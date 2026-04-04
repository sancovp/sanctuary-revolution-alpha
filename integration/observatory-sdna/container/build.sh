#!/bin/bash
# Build repo-lord container image

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Config
IMAGE_NAME="${IMAGE_NAME:-repo-lord}"
REGISTRY="${REGISTRY:-ghcr.io/isaacwr}"
TAG="${TAG:-latest}"
FULL_IMAGE="$REGISTRY/$IMAGE_NAME:$TAG"

usage() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  build     Build the image locally (default)"
    echo "  push      Build and push to registry"
    echo "  tag       Tag current build with version"
    echo "  clean     Remove local images"
    echo ""
    echo "Environment:"
    echo "  IMAGE_NAME  Image name (default: repo-lord)"
    echo "  REGISTRY    Registry (default: ghcr.io/isaacwr)"
    echo "  TAG         Tag (default: latest)"
    exit 1
}

stage() {
    echo "Staging Python packages into build context..."

    # Copy llegos (local package, cave dependency)
    rm -rf llegos
    cp -r /tmp/sanctuary-system/llegos llegos
    rm -rf llegos/build llegos/*.egg-info llegos/__pycache__

    # Copy sdna (cave dependency)
    rm -rf sdna
    cp -r /tmp/sdna-repo sdna
    rm -rf sdna/build sdna/*.egg-info sdna/__pycache__

    # Copy cave-harness package (CAVEHTTPServer + agent types)
    rm -rf cave-harness
    cp -r /home/GOD/gnosys-plugin-v2/application/cave cave-harness
    rm -rf cave-harness/build cave-harness/*.egg-info cave-harness/__pycache__

    # Copy heaven-framework (BaseHeavenAgent runtime)
    rm -rf heaven-framework
    cp -r /home/GOD/gnosys-plugin-v2/base/heaven-framework heaven-framework
    rm -rf heaven-framework/build heaven-framework/*.egg-info heaven-framework/__pycache__

    # Copy grug_agent.py (just the module, not full observatory-sdna)
    cp /home/GOD/gnosys-plugin-v2/integration/observatory-sdna/observatory/grug_agent.py grug_agent.py

    # Copy grug_server.py entry point
    cp /home/GOD/gnosys-plugin-v2/integration/observatory-sdna/grug_server.py grug_server.py

    echo "Staged."
}

unstage() {
    rm -rf llegos sdna cave-harness heaven-framework grug_agent.py grug_server.py
}

build() {
    stage
    echo "Building $IMAGE_NAME..."
    docker build -t "$IMAGE_NAME:$TAG" -t "$FULL_IMAGE" .
    unstage
    echo ""
    echo "Built: $IMAGE_NAME:$TAG"
    echo "       $FULL_IMAGE"
}

push() {
    build
    echo ""
    echo "Pushing to $REGISTRY..."
    docker push "$FULL_IMAGE"
    echo "Pushed: $FULL_IMAGE"
}

tag_version() {
    VERSION="$1"
    if [ -z "$VERSION" ]; then
        echo "Usage: $0 tag <version>"
        echo "Example: $0 tag v1.0.0"
        exit 1
    fi

    docker tag "$IMAGE_NAME:$TAG" "$REGISTRY/$IMAGE_NAME:$VERSION"
    echo "Tagged: $REGISTRY/$IMAGE_NAME:$VERSION"
}

clean() {
    echo "Removing local images..."
    docker rmi "$IMAGE_NAME:$TAG" 2>/dev/null || true
    docker rmi "$FULL_IMAGE" 2>/dev/null || true
    echo "Cleaned."
}

case "${1:-build}" in
    build)
        build
        ;;
    push)
        push
        ;;
    tag)
        tag_version "$2"
        ;;
    clean)
        clean
        ;;
    *)
        usage
        ;;
esac
