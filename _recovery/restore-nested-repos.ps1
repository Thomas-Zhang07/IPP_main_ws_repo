# Attach the bundled git history to the snapshot working trees.
# Run from anywhere; paths are resolved relative to this script's parent.
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot

# path relative to workspace root -> @(bundle file, branch, remote url)
$repos = [ordered]@{
  'demo'                             = @('demo.bundle',                              'main',   'https://github.com/Thomas-Zhang07/LUIS_IPP_demo.git')
  'fpga\primary'                     = @('fpga_primary.bundle',                      'main',   'https://github.com/Thomas-Zhang07/sonic_surface_directional_speaker_fpga_primary.git')
  'fpga\secondary'                   = @('fpga_secondary.bundle',                    'main',   'https://github.com/Thomas-Zhang07/sonic_surface_directional_speaker_fpga_secondary.git')
  'fpga\reference\secondary-original'= @('fpga_reference_secondary-original.bundle', 'master', '')
  'other_fpga_code\fpga_code_bak'    = @('other_fpga_code_fpga_code_bak.bundle',     'main',   'https://github.com/Thomas-Zhang07/LUIS_demo_fpga.git')
  'SonicSurface'                     = @('SonicSurface.bundle',                      'main',   'https://github.com/upnalab/SonicSurface.git')
}

foreach ($path in $repos.Keys) {
  $bundleFile, $branch, $remote = $repos[$path]
  $target = Join-Path $root $path
  $bundle = Join-Path $PSScriptRoot (Join-Path 'bundles' $bundleFile)

  if (-not (Test-Path $target)) { Write-Host "skip  $path (directory missing)"; continue }
  if (Test-Path (Join-Path $target '.git')) { Write-Host "skip  $path (already a git repo)"; continue }
  if (-not (Test-Path $bundle)) { Write-Host "skip  $path (bundle missing)"; continue }

  Write-Host "init  $path"
  git -C $target init -q -b $branch
  if ($remote) { git -C $target remote add origin $remote }
  git -C $target fetch -q $bundle "refs/heads/*:refs/heads/*" "refs/tags/*:refs/tags/*"
  git -C $target reset -q
  Write-Host ("done  {0} -> {1}" -f $path, (git -C $target rev-parse --short HEAD))
}
