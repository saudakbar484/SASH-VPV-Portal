# Allow other devices on your Wi-Fi to reach the dev servers (run as Administrator).
# Only needed if phones/laptops cannot open the Network URL.

$rules = @(
    @{ Name = "Palm Vein Frontend (5173)"; Port = 5173 },
    @{ Name = "Palm Vein Backend (8000)"; Port = 8000 }
)

foreach ($rule in $rules) {
    $existing = Get-NetFirewallRule -DisplayName $rule.Name -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "Rule already exists: $($rule.Name)"
        continue
    }
    New-NetFirewallRule `
        -DisplayName $rule.Name `
        -Direction Inbound `
        -Action Allow `
        -Protocol TCP `
        -LocalPort $rule.Port | Out-Null
    Write-Host "Added firewall rule: $($rule.Name)"
}

Write-Host ""
Write-Host "Run: python scripts/network_urls.py"
Write-Host "Then open the Network URL on your phone (same Wi-Fi as this PC)."
