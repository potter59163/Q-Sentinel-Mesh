$Bucket = $args[0]

if (-not $Bucket) {
  Write-Error "Usage: powershell -ExecutionPolicy Bypass -File infra/upload-runtime-assets.ps1 <bucket-name>"
  exit 1
}

aws s3 sync weights "s3://$Bucket/weights/" --region ap-southeast-7
aws s3 sync data/samples "s3://$Bucket/data/samples/" --exclude ".cache/*" --region ap-southeast-7

Write-Host "Uploaded runtime assets to s3://$Bucket"
