function Add-VideoNewsFfmpegToPath {
    if ((Get-Command ffmpeg -ErrorAction SilentlyContinue) -and
        (Get-Command ffprobe -ErrorAction SilentlyContinue)) { return }
    $packages = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages'
    $exe = Get-ChildItem -Path $packages -Filter ffmpeg.exe `
        -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -like '*Gyan.FFmpeg*' } |
        Where-Object { Test-Path -LiteralPath (Join-Path $_.DirectoryName 'ffprobe.exe') } |
        Select-Object -First 1
    if (-not $exe) { return }
    $bin = $exe.DirectoryName
    $env:Path = "$bin;$env:Path"
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    if (($userPath -split ';') -notcontains $bin) {
        [Environment]::SetEnvironmentVariable('Path', "$userPath;$bin", 'User')
    }
}
