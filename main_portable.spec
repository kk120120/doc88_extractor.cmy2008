name: Build doc88_extractor Portable (Windows x64)

on:
  push:
    branches: [ main, master ]
    tags: [ 'v*' ]
  pull_request:
    branches: [ main, master ]
  workflow_dispatch:

jobs:
  build:
    runs-on: windows-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.10'
        architecture: 'x64'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install pyinstaller retrying pypdf requests pywin32

    - name: Download JRE (Microsoft Build of OpenJDK 17)
      shell: powershell
      run: |
        Write-Host "Downloading Microsoft Build of OpenJDK 17..."
        $jreUrl = "https://aka.ms/download-jdk/microsoft-jdk-17.0.14-windows-x64.zip"
        $outputPath = "jre.zip"
        Invoke-WebRequest -Uri $jreUrl -OutFile $outputPath -UseBasicParsing
        
        Write-Host "Extracting JRE..."
        Expand-Archive -Path $outputPath -DestinationPath . -Force
        
        # Rename JDK directory to jre
        $jdkDir = Get-ChildItem -Directory -Filter "*jdk*" | Select-Object -First 1
        if ($jdkDir) {
            Rename-Item -Path $jdkDir.FullName -NewName "jre"
            Write-Host "JRE ready at: $(Get-Location)\jre"
        } else {
            Write-Host "Error: JDK directory not found!"
            exit 1
        }
        
        Remove-Item $outputPath -Force

    - name: Build with PyInstaller (Single Directory)
      run: |
        pyinstaller --clean --noconfirm main_portable.spec

    - name: Create launcher script
      shell: powershell
      run: |
        $launcherContent = @"
@echo off
chcp 65001 >nul
title doc88_extractor
cd /d "%~dp0"

REM Set up bundled JRE
if exist "jre" (
    echo Using bundled Java...
    set "JAVA_HOME=%~dp0jre"
    set "PATH=%JAVA_HOME%\bin;%PATH%"
)

REM Run the main program
doc88_extractor.exe

if errorlevel 1 (
    echo.
    echo Program exited with error code: %errorlevel%
    echo.
    pause
)
"@
        $launcherContent | Out-File -FilePath "dist/doc88_extractor/启动.bat" -Encoding ASCII

    - name: Create README for package
      shell: powershell
      run: |
        $readmeContent = @"
# doc88_extractor - Portable Version

## 系统要求
- Windows 7 或更高版本 (64位)
- 无需安装 Python 或 Java（已内置）

## 使用方法
1. 解压此文件夹到任意位置
2. 双击运行 "启动.bat"（推荐）
3. 或直接运行 "doc88_extractor.exe"

## 内置组件
- Python 3.10（已打包）
- Microsoft Build of OpenJDK 17
- 所有依赖项

## 注意
- 首次运行会自动下载 ffdec 工具
- PDF 文件会保存在 "docs" 文件夹中
"@
        $readmeContent | Out-File -FilePath "dist/doc88_extractor/README.txt" -Encoding UTF8

    - name: Package the distribution
      shell: powershell
      run: |
        $dateStr = Get-Date -Format 'yyyyMMdd'
        if ('${{ github.ref_name }}'.StartsWith('v')) {
            $version = '${{ github.ref_name }}'
        } else {
            $version = "dev-$dateStr"
        }
        $archiveName = "doc88_extractor-portable-windows-x64-$version"
        
        Write-Host "Creating 7z archive..."
        choco install 7zip -y
        7z a -t7z -m0=lzma2 -mx=9 -mfb=64 -md=32m -ms=on "$archiveName.7z" ".\dist\doc88_extractor\*"
        
        Write-Host "Creating zip archive..."
        Compress-Archive -Path "dist/doc88_extractor/*" -DestinationPath "$archiveName.zip" -Force
        
        echo "ARCHIVE_7Z=$archiveName.7z" >> $env:GITHUB_ENV
        echo "ARCHIVE_ZIP=$archiveName.zip" >> $env:GITHUB_ENV

    - name: Upload artifacts
      uses: actions/upload-artifact@v4
      with:
        name: doc88_extractor-portable-windows-x64
        path: |
          ${{ env.ARCHIVE_7Z }}
          ${{ env.ARCHIVE_ZIP }}

    - name: Upload release assets
      if: startsWith(github.ref, 'refs/tags/v')
      uses: softprops/action-gh-release@v1
      with:
        files: |
          ${{ env.ARCHIVE_7Z }}
          ${{ env.ARCHIVE_ZIP }}
        draft: false
        prerelease: false
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
