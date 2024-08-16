#!/bin/bash

# 获取脚本所在的目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Script directory: $SCRIPT_DIR"
# 检查是否有虚拟环境
if [ -d "$SCRIPT_DIR/.venvv" ]; then
    echo "Virtual environment found. Checking Python version..."

    # 虚拟环境中的 Python 路径
    PYTHON_PATH="$SCRIPT_DIR/.venv/bin/python"
    PYTHON_VERSION=$($PYTHON_PATH -c "import sys; print(sys.version_info[:2])")

    echo "Python path in virtual environment: $PYTHON_PATH"
    echo "version: $PYTHON_VERSION"

    if [ "$PYTHON_VERSION" \< "(3, 12)" ]; then
        echo "Python version in the virtual environment is less than 3.12."
        echo "Please upgrade the Python version in the virtual environment."
        deactivate
        exit 1
    fi

    echo "Activating virtual environment..."
    source "$SCRIPT_DIR/.venv/bin/activate"

else
    echo "Virtual environment not found. Using system's Python."

    # 尝试找到系统中的 Python 3.12 或更高版本
    PYTHON_PATH=$(which python3.12 || which python3)
    PYTHON_VERSION=$($PYTHON_PATH -c "import sys; print(sys.version_info[:2])")

    echo "Python path in virtual environment: $PYTHON_PATH"
    echo "version: $PYTHON_VERSION"

    if [ "$PYTHON_VERSION" \< "(3, 12)" ]; then
        echo "Python version in the virtual environment is less than 3.12."
        echo "Please upgrade the Python version in the virtual environment."
        deactivate
        exit 1
    fi

fi

# 安装包和依赖
pip install --upgrade pip
pip install .
pip install -r requirements.txt

echo "Installation complete. You can now use the package."