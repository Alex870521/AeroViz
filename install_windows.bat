@echo off
setlocal enabledelayedexpansion

REM 將目錄切換到腳本所在目錄
cd /d "%~dp0"

REM 檢查是否存在虛擬環境
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
    echo Virtual environment activated.

    REM 檢查虛擬環境中的 python 版本
    echo Checking Python version in the virtual environment...

    REM 使用更簡單的 Python 命令捕獲版本信息
    for /f "delims=" %%V in ('python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do (
        set "PYTHON_VERSION=%%V"
    )
    echo Python version is: !PYTHON_VERSION!

    REM 提取主要和次要版本号
    for /f "tokens=1,2 delims=." %%a in ("!PYTHON_VERSION!") do (
        set "major=%%a" echo %%a
        set "minor=%%b" echo %%b
    )

    REM 比较版本号是否小于 3.12
    if !major! LSS 3 (
        echo Python version is too low. Please use Python 3.12 or higher.
        pause
        exit /b
    ) else if !major! EQU 3 if !minor! LSS 12 (
        echo Python version is too low. Please use Python 3.12 or higher.
        pause
        exit /b
    )

) else (
    echo No virtual environment found.
    set /p CREATE_VENV="Do you want to create a virtual environment? (y/n): "
    if /i "!CREATE_VENV!"=="y" (
        py -m venv venv
        echo Virtual environment created.
        call venv\Scripts\activate.bat
        echo Virtual environment activated.

    ) else (
        echo Searching for Python 3.12 or higher...
        REM 如果沒有找到虛擬環境，則查 python 預設路徑
        for %%P in ("C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python312\python.exe") do (
            %%P -c "import sys; exit(0) if sys.version_info >= (3, 12) else exit(1)"
            if not errorlevel 1 (
                echo Found Python 3.12+ at %%P

            ) else (
                echo No suitable Python 3.12+ found. Please install Python 3.12 or higher.
                pause
                exit /b
            )
        )
    )
)
echo Installing package and dependencies...
py -m pip install --upgrade pip
py -m pip install .
py -m pip install -r requirements.txt
echo Installation complete. You can now use the package.

pause
endlocal
