# Windows 내장 OCR(WinRT, 한국어 엔진)로 디렉터리 내 모든 PNG의 단어와 좌표를 JSON으로 출력한다.
# 사용: powershell -ExecutionPolicy Bypass -File ocr_words.ps1 -Dir <png 폴더> -Out <결과 json 경로>
param(
    [Parameter(Mandatory = $true)][string]$Dir,
    [Parameter(Mandatory = $true)][string]$Out
)

Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType = WindowsRuntime]

$awaitMethod = [System.WindowsRuntimeSystemExtensions].GetMethods() |
    Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' } |
    Select-Object -First 1

function Await($op, $resultType) {
    $t = $awaitMethod.MakeGenericMethod($resultType).Invoke($null, @($op))
    $t.Wait() | Out-Null
    $t.Result
}

$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
if (-not $engine) { Write-Error "OCR 엔진 생성 실패 (한국어 언어팩 필요)"; exit 1 }

$result = @{}
foreach ($png in Get-ChildItem -Path $Dir -Filter *.png | Sort-Object Name) {
    $file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($png.FullName)) ([Windows.Storage.StorageFile])
    $stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
    $decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
    $ocr = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
    $stream.Dispose()

    $words = New-Object System.Collections.ArrayList
    foreach ($line in $ocr.Lines) {
        foreach ($w in $line.Words) {
            $null = $words.Add(@(
                    [double]$w.BoundingRect.X,
                    [double]$w.BoundingRect.Y,
                    [double]($w.BoundingRect.X + $w.BoundingRect.Width),
                    [double]($w.BoundingRect.Y + $w.BoundingRect.Height),
                    $w.Text
                ))
        }
    }
    $result[$png.Name] = $words
}

$json = ConvertTo-Json -InputObject $result -Depth 5 -Compress
[System.IO.File]::WriteAllText($Out, $json, [System.Text.Encoding]::UTF8)
Write-Output "OK $($result.Count) pages"
