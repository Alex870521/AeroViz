@echo off
setlocal enabledelayedexpansion

REM 将目录切换到脚本所在目录
cd /d "%~dp0"

REM 检查是否存在虚拟环境
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
    echo Virtual environment activated.

    REM 检查虚拟环境中的 Python 版本
    echo Checking Python version in the virtual environment...
    for /f "delims=" %%V in ('python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do (
        set "PYTHON_VERSION=%%V"
    )
    echo Python version is: !PYTHON_VERSION!

    for /f "tokens=1,2 delims=." %%a in ("!PYTHON_VERSION!") do (
        set "major=%%a"
        set "minor=%%b"
    )

    if !major! LSS 3 (
        goto :version_error
    ) else if !major! EQU 3 if !minor! LSS 12 (
        goto :version_error
    )
) else (
    echo No virtual environment found.
    set /p CREATE_VENV="Do you want to create a virtual environment? (y/n): "
    if /i "!CREATE_VENV!"=="y" (
        py -3.12 -m venv venv || (
            echo Failed to create virtual environment. Make sure Python 3.12+ is installed.
            goto :error
        )
        echo Virtual environment created.
        call venv\Scripts\activate.bat
        echo Virtual environment activated.
    ) else (
        echo Searching for Python 3.12 or higher...
        where py >nul 2>&1 || (
            echo Python launcher (py) not found. Please install Python 3.12 or higher.
            goto :error
        )
        py -3.12 -c "import sys; exit(0)" >nul 2>&1 || (
            echo No suitable Python 3.12+ found. Please install Python 3.12 or higher.
            goto :error
        )
        echo Found Python 3.12+
    )
)

echo Installing package and dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install .
echo Installation complete. You can now use the package.
goto :end

:version_error
echo Python version is too low. Please use Python 3.12 or higher.
goto :error

:error
pause
exit /b 1

:end
pause
endlocal
exit /b 0