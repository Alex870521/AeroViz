#!/bin/bash

# 获取脚本所在的目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Script directory: $SCRIPT_DIR"

# 检查 Python 版本的函数
check_python_version() {
    local python_path=$1
    if [ ! -x "$python_path" ]; then
        echo "Python executable not found at $python_path"
        return 1
    fi
    local python_version=$($python_path -c "import sys; print('{}.{}'.format(*sys.version_info[:2]))")
    echo "Python version: $python_version"
    if [ "$(echo "$python_version 3.12" | awk '{print ($1 < $2)}')" -eq 1 ]; then
        echo "Python version is less than 3.12."
        return 1
    fi
    return 0
}

# 检查是否有虚拟环境
if [ -d "$SCRIPT_DIR/.venv" ]; then
    echo "Virtual environment found."
    PYTHON_PATH="$SCRIPT_DIR/.venv/bin/python"
    if check_python_version "$PYTHON_PATH"; then
        echo "Activating virtual environment..."
        source "$SCRIPT_DIR/.venv/bin/activate"
    else
        echo "Please upgrade the Python version in the virtual environment."
        exit 1
    fi
else
    echo "Virtual environment not found. Using system's Python."
    PYTHON_PATH=$(command -v python3.12 || command -v python3)
    if ! check_python_version "$PYTHON_PATH"; then
        echo "Please install Python 3.12 or higher."
        exit 1
    fi

    echo "Creating a new virtual environment..."
    python3 -m venv "$SCRIPT_DIR/.venv"
    source "$SCRIPT_DIR/.venv/bin/activate"
fi

# 安装包和依赖
pip install --upgrade pip
pip install -r requirements.txt
pip install .

echo "Installation complete. You can now use the package."