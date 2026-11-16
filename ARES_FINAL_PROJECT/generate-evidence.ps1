$ErrorActionPreference = 'Stop'

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$EvidenceDirectory = $PSScriptRoot
$BaselinePath = Join-Path $EvidenceDirectory 'BASELINE_COMMIT.txt'

if (-not (Test-Path $BaselinePath)) {
    throw "Baseline file not found: $BaselinePath"
}

$BaselineText = Get-Content -Path $BaselinePath -Raw
$BaselineHash = ($BaselineText -split ' \| ', 2)[0].Trim()
if ($BaselineHash -notmatch '^[0-9a-fA-F]{40,64}$') {
    throw "BASELINE_COMMIT.txt does not start with a valid full Git hash."
}

$Utf8NoBom = New-Object System.Text.UTF8Encoding $false

function Export-GitOutput {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FileName,
        [Parameter(Mandatory = $true)]
        [string[]]$GitArguments
    )

    $Output = & git -C $ProjectRoot @GitArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Git command failed while generating $FileName."
    }

    $Content = ($Output | ForEach-Object { [string]$_ }) -join "`r`n"
    [System.IO.File]::WriteAllText(
        (Join-Path $EvidenceDirectory $FileName),
        $Content,
        $Utf8NoBom
    )
}

Export-GitOutput 'GIT_HISTORY.txt' @(
    'log',
    '--since=2026-11-16 15:00:00',
    '--until=2026-11-16 18:00:00',
    '--date=iso',
    '--pretty=format:%h | %an | %ad | %s'
)

Export-GitOutput 'GIT_COMMIT_DETAILS.txt' @(
    'log',
    '--since=2026-11-16 15:00:00',
    '--until=2026-11-16 18:00:00',
    '--stat',
    '--date=iso'
)

Export-GitOutput 'GIT_ALL_COMMITTED_CHANGES.patch' @(
    'diff',
    '--binary',
    "$BaselineHash..HEAD"
)

Export-GitOutput 'GIT_UNCOMMITTED_CHANGES.patch' @(
    'diff',
    '--binary'
)

Export-GitOutput 'GIT_STATUS.txt' @(
    'status',
    '--short'
)

Export-GitOutput 'GIT_DIFF_STAT.txt' @(
    'diff',
    "$BaselineHash..HEAD",
    '--stat'
)

Write-Output "Evidence exports written to $EvidenceDirectory"
