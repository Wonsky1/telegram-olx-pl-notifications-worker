echo "Logging in to Docker Hub..."
docker login

echo "Building and pushing Docker image..."
echo "------------------------------------"
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    -t wonsky/topn-worker:stg \
    --push \
    .
echo "------------------------------------"
echo "Done!"
