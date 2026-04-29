#!/bin/bash
# Package Lambda function with dependencies

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"  # Go up two levels from dev/scripts/
SRC_DIR="$PROJECT_ROOT/src"
PACKAGE_DIR="$PROJECT_ROOT/lambda-package"
ZIP_FILE="$PROJECT_ROOT/lambda-package.zip"

echo "Cleaning previous package..."
rm -rf "$PACKAGE_DIR" "$ZIP_FILE"

echo "Creating package directory..."
mkdir -p "$PACKAGE_DIR"

echo "Installing dependencies..."
pip install -q -r "$PROJECT_ROOT/requirements.txt" -t "$PACKAGE_DIR"

echo "Copying source code..."
cp "$SRC_DIR/lambda_function.py" "$PACKAGE_DIR/"
cp -r "$SRC_DIR/scanner" "$PACKAGE_DIR/"

echo "Creating deployment package..."
cd "$PACKAGE_DIR"
zip -q -r "$ZIP_FILE" .

echo "Deployment package created: $ZIP_FILE"
ls -lh "$ZIP_FILE"
