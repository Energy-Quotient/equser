#!/bin/bash
# Release script for equser PyPI package
#
# Usage:
#   ./scripts/release.sh [--test]    # Build and upload to TestPyPI
#   ./scripts/release.sh             # Build and upload to PyPI (production)
#
# Prerequisites:
#   uv (https://docs.astral.sh/uv/) — build + publish run via uv/uvx
#
# Configuration:
#   Create ~/.pypirc with your API tokens:
#   [pypi]
#   username = __token__
#   password = pypi-YOUR-TOKEN
#
#   [testpypi]
#   username = __token__
#   password = pypi-YOUR-TEST-TOKEN

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_step() {
    echo -e "${GREEN}==>${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}Warning:${NC} $1"
}

echo_error() {
    echo -e "${RED}Error:${NC} $1"
}

# Parse arguments
USE_TESTPYPI=false
if [[ "$1" == "--test" ]]; then
    USE_TESTPYPI=true
fi

# Get version from _version.py
VERSION=$(python3 -c "exec(open('equser/_version.py').read()); print(__version__)")
echo_step "Preparing release for equser v${VERSION}"

# Check for uncommitted changes
if [[ -n $(git status --porcelain) ]]; then
    echo_warn "You have uncommitted changes. Consider committing first."
    read -p "Continue anyway? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if version tag exists
if git rev-parse "v${VERSION}" >/dev/null 2>&1; then
    echo_error "Tag v${VERSION} already exists. Update _version.py first."
    exit 1
fi

# Clean previous builds
echo_step "Cleaning previous builds..."
rm -rf dist/ build/ *.egg-info/

# Install/upgrade build tools
echo_step "Checking build tools..."
command -v uv >/dev/null || { echo_error "uv is required (https://docs.astral.sh/uv/)"; exit 1; }

# Build the package
echo_step "Building package..."
uv build

# Show what was built
echo_step "Built packages:"
ls -la dist/

# Public-safety gate: scan the built artifacts for secrets / internal-only
# detail before anything is uploaded. Fail closed.
echo_step "Scanning built artifacts for public-safety issues..."
if ! python3 scripts/check-public-safe.py --dist; then
    echo_error "Public-safety scan failed. Aborting release (nothing uploaded)."
    exit 1
fi

# Verify the package
echo_step "Verifying package with twine..."
uvx twine check dist/*

# Upload
if [[ "$USE_TESTPYPI" == true ]]; then
    echo_step "Uploading to TestPyPI..."
    uvx twine upload --repository testpypi dist/*
    echo ""
    echo_step "Package uploaded to TestPyPI!"
    echo "Test installation with:"
    echo "  pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ equser==${VERSION}"
else
    echo_step "Uploading to PyPI..."
    read -p "Upload to production PyPI? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        uvx twine upload dist/*
        echo ""
        echo_step "Package uploaded to PyPI!"
        echo "Install with: pip install equser==${VERSION}"

        # Create git tag
        echo_step "Creating git tag v${VERSION}..."
        git tag -a "v${VERSION}" -m "Release v${VERSION}"
        echo "Don't forget to push the tag: git push origin v${VERSION}"
    else
        echo "Upload cancelled."
    fi
fi

echo ""
echo_step "Done!"
