param([Parameter(Mandatory=$true)][string]$Token)

$headers = @{ Authorization = "token $Token" }
$releases = Invoke-RestMethod -Headers $headers 'https://api.github.com/repos/Joey-Farah/Slippi-Ranked-Stats/releases'

foreach ($release in $releases) {
    Write-Host $release.tag_name -ForegroundColor Cyan
    foreach ($asset in $release.assets) {
        Write-Host "  $($asset.name): $($asset.download_count) downloads"
    }
}
