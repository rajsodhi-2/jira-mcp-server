@echo off
REM Check if required environment variables are set
if "%JIRA_API_TOKEN%"=="" (
    echo ERROR: JIRA_API_TOKEN environment variable is not set. 1>&2
    echo Please set it in .env file or using: set JIRA_API_TOKEN=your_token_here 1>&2
    exit /b 1
)

REM Activate virtual environment
REM Note: Virtual environment is in the same directory
if exist "%~dp0planning_board_scrape_venv\Scripts\activate.bat" (
    call "%~dp0planning_board_scrape_venv\Scripts\activate.bat" >nul 2>&1
) else (
    echo ERROR: Virtual environment not found at %~dp0planning_board_scrape_venv 1>&2
    exit /b 1
)

REM Verify we're in the virtual environment by checking Python path
where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH after venv activation 1>&2
    exit /b 1
)

REM Start the primary JIRA server
REM %~dp0 refers to the directory where this batch file is located
python "%~dp0jira_mcp_server.py" 2>&1
