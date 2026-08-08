Invoke-RestMethod -Method POST http://localhost:8081/api/failures/payment/db_pool
1..30 | ForEach-Object { try { Invoke-WebRequest http://localhost:8080/checkout -UseBasicParsing | Out-Null } catch {} }
Invoke-RestMethod -Method POST http://localhost:8081/api/investigations -ContentType application/json -Body '{"question":"Why is checkout failing?"}' | ConvertTo-Json -Depth 12
