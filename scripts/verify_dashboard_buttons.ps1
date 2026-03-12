$ErrorActionPreference = "Stop"

$root = "C:\Users\1\OneDrive - Institute of Business Administration\Desktop\Exam"
$dashboardRoot = Join-Path $root "dashboard\markaz-dashboard"
$serviceRole = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ5bnpjamZ3eHB0cW92Z3lpa25qIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjMzODk1NSwiZXhwIjoyMDg3OTE0OTU1fQ.G3t7ZDqxmLpHO0xxjgtfwtSq937UNPLVtk5tRjjIqUk"
$supabaseUrl = "https://vynzcjfwxptqovgyiknj.supabase.co"
$backendApiKey = "markaz_exam_system_secret_2026"
$localBackendUrl = "http://127.0.0.1:8010"
$localDashboardUrl = "http://127.0.0.1:3004"
$sessionsPageExamId = "911d7c8b-40f6-4944-939a-dd984a19a5b2"
$pausedSessionId = "8a92a405-3ef6-49b7-b0ca-cc0be97cdd33"
$analyzeSessionId = "a66abe10-6741-476c-b0ee-85ecbe60d32b"
$playwrightScript = Join-Path $dashboardRoot ".codex-dashboard-verify.js"
$playwrightOutput = Join-Path $dashboardRoot ".codex-dashboard-verify-results.json"

$headers = @{
    apikey = $serviceRole
    Authorization = "Bearer $serviceRole"
    Prefer = "return=representation"
    "Content-Type" = "application/json"
}

$backendJob = $null
$localDashJob = $null
$createdExamId = $null
$createdSessionId = $null

function Wait-Http([string]$url, [int]$timeoutSeconds) {
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    while ($sw.Elapsed.TotalSeconds -lt $timeoutSeconds) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 5
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return $true
            }
        } catch {
        }
        Start-Sleep -Seconds 2
    }

    return $false
}

try {
    $backendJob = Start-Job -ArgumentList $root -ScriptBlock {
        param($jobRoot)
        Set-Location $jobRoot
        & "$jobRoot\venv\Scripts\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8010
    }

    $localDashJob = Start-Job -ArgumentList $dashboardRoot, $backendApiKey -ScriptBlock {
        param($jobRoot, $apiKey)
        Set-Location $jobRoot
        $env:BACKEND_URL = "http://127.0.0.1:8010"
        $env:BACKEND_API_KEY = $apiKey
        npm run dev -- --hostname 127.0.0.1 --port 3004
    }

    if (-not (Wait-Http "$localBackendUrl/health" 60)) {
        throw "Local backend did not become ready on port 8010."
    }

    if (-not (Wait-Http "$localDashboardUrl/exams" 120)) {
        throw "Local dashboard did not become ready on port 3004."
    }

    $student = Invoke-RestMethod -Method Get -Headers $headers -Uri "$supabaseUrl/rest/v1/students?erp=eq.28350&select=id&limit=1"
    if (-not $student -or $student.Count -eq 0) {
        throw "Could not find student ERP 28350 for the disposable fallback test."
    }

    $now = [DateTime]::UtcNow
    $examName = "CODEX FALLBACK TEST $($now.ToString('yyyyMMddHHmmss'))"
    $examPayload = @{
        exam_name = $examName
        class_number = "CODEX"
        start_time = $now.AddMinutes(-10).ToString("o")
        end_time = $now.AddMinutes(50).ToString("o")
        access_code = "C$($now.ToString('HHmmss'))"
        force_stop = $false
    } | ConvertTo-Json
    $createdExam = Invoke-RestMethod -Method Post -Headers $headers -Uri "$supabaseUrl/rest/v1/exams" -Body $examPayload
    $createdExamId = $createdExam[0].id

    $sessionPayload = @{
        student_id = $student[0].id
        exam_id = $createdExamId
        status = "active"
        session_start = $now.ToString("o")
        last_heartbeat_at = $now.ToString("o")
    } | ConvertTo-Json
    $createdSession = Invoke-RestMethod -Method Post -Headers $headers -Uri "$supabaseUrl/rest/v1/exam_sessions" -Body $sessionPayload
    $createdSessionId = $createdSession[0].id

    @'
const fs = require("fs");
const { chromium } = require("playwright");

const localDashboardUrl = process.env.CODEX_LOCAL_DASHBOARD_URL;
const sessionsPageExamId = process.env.CODEX_SESSIONS_EXAM_ID;
const pausedSessionId = process.env.CODEX_PAUSED_SESSION_ID;
const analyzeSessionId = process.env.CODEX_ANALYZE_SESSION_ID;
const outputPath = process.env.CODEX_PLAYWRIGHT_OUTPUT;

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  page.on("dialog", async dialog => {
    await dialog.accept();
  });

  const results = [];

  try {
    await page.goto(`${localDashboardUrl}/sessions?exam_id=${sessionsPageExamId}`, { waitUntil: "networkidle", timeout: 120000 });
    results.push({
      name: "bulkAnalyzeRemoved",
      pass: (await page.getByRole("button", { name: /Analyze Sessions/i }).count()) === 0,
      detail: "Sessions page rendered without the removed bulk analyze button.",
    });

    await page.goto(`${localDashboardUrl}/sessions/${pausedSessionId}`, { waitUntil: "networkidle", timeout: 120000 });
    const restartVisibleBefore = (await page.getByRole("button", { name: /^Restart Session$/i }).count()) === 1;
    const pauseVisibleBefore = (await page.getByRole("button", { name: /Pause Session/i }).count()) > 0;
    const restartResponsePromise = page.waitForResponse(
      response => response.url().includes(`/api/restart/${pausedSessionId}`) && response.request().method() === "POST",
      { timeout: 20000 },
    );
    await page.getByRole("button", { name: /^Restart Session$/i }).click();
    const restartResponse = await restartResponsePromise;
    await page.waitForTimeout(2000);
    await page.reload({ waitUntil: "networkidle", timeout: 120000 });
    const pauseVisibleAfter = (await page.getByRole("button", { name: /Pause Session/i }).count()) > 0;
    const restartVisibleAfter = (await page.getByRole("button", { name: /^Restart Session$/i }).count()) > 0;
    results.push({
      name: "restartButtonPausedOnly",
      pass: restartVisibleBefore && !pauseVisibleBefore && restartResponse.status() === 200 && pauseVisibleAfter && !restartVisibleAfter,
      detail: {
        restartVisibleBefore,
        pauseVisibleBefore,
        restartStatus: restartResponse.status(),
        pauseVisibleAfter,
        restartVisibleAfter,
      },
    });

    const restorePauseResponse = await page.request.post(`${localDashboardUrl}/api/stop/${pausedSessionId}`);
    results.push({
      name: "restorePausedSession",
      pass: restorePauseResponse.status() === 200,
      detail: { restorePauseStatus: restorePauseResponse.status() },
    });

    await page.goto(`${localDashboardUrl}/sessions/${analyzeSessionId}`, { waitUntil: "networkidle", timeout: 120000 });
    const startedAt = Date.now();
    const analyzeResponsePromise = page.waitForResponse(
      response => response.url().includes(`/api/analyze/${analyzeSessionId}`) && response.request().method() === "POST",
      { timeout: 60000 },
    );
    await page.getByRole("button", { name: /Analyze with AI/i }).click();
    const analyzeResponse = await analyzeResponsePromise;
    const analyzeElapsedMs = Date.now() - startedAt;
    let analyzeBody = null;
    try {
      analyzeBody = await analyzeResponse.json();
    } catch {
      analyzeBody = { parseError: true };
    }
    const analyzeMessage = await page.locator("text=/Error:|detected/").first().textContent({ timeout: 10000 }).catch(() => null);
    results.push({
      name: "sessionAnalyzeFastPath",
      pass: analyzeElapsedMs <= 50000,
      detail: {
        status: analyzeResponse.status(),
        elapsedMs: analyzeElapsedMs,
        body: analyzeBody,
        message: analyzeMessage,
      },
    });

  } finally {
    await browser.close();
  }

  fs.writeFileSync(outputPath, JSON.stringify(results, null, 2));
})();
'@ | Set-Content -Path $playwrightScript -Encoding UTF8

    $env:CODEX_LOCAL_DASHBOARD_URL = $localDashboardUrl
    $env:CODEX_SESSIONS_EXAM_ID = $sessionsPageExamId
    $env:CODEX_PAUSED_SESSION_ID = $pausedSessionId
    $env:CODEX_ANALYZE_SESSION_ID = $analyzeSessionId
    $env:CODEX_PLAYWRIGHT_OUTPUT = $playwrightOutput

    & node $playwrightScript

    $localUiResults = Get-Content -Path $playwrightOutput -Raw | ConvertFrom-Json

    Stop-Job -Job $backendJob -ErrorAction SilentlyContinue | Out-Null
    Remove-Job -Job $backendJob -Force -ErrorAction SilentlyContinue | Out-Null
    $backendJob = $null

    @'
const fs = require("fs");
const { chromium } = require("playwright");

const localDashboardUrl = process.env.CODEX_LOCAL_DASHBOARD_URL;
const disposableExamName = process.env.CODEX_DISPOSABLE_EXAM_NAME;
const outputPath = process.env.CODEX_PLAYWRIGHT_OUTPUT;

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  page.on("dialog", async dialog => {
    await dialog.accept();
  });
  const results = [];

  try {
    await page.goto(`${localDashboardUrl}/exams`, { waitUntil: "networkidle", timeout: 120000 });
    const examCard = page.locator(".aesthetic-card").filter({ hasText: disposableExamName }).first();
    await examCard.waitFor({ state: "visible", timeout: 20000 });
    await examCard.getByRole("button", { name: /End Deployment/i }).click();
    await page.waitForTimeout(2500);
    const endedTextVisible = (await examCard.getByText(/Already Ended|Ended/i).count()) > 0;
    results.push({
      name: "examFallbackButtonFlow",
      pass: endedTextVisible,
      detail: { endedTextVisible },
    });
  } finally {
    await browser.close();
  }

  fs.writeFileSync(outputPath, JSON.stringify(results, null, 2));
})();
'@ | Set-Content -Path $playwrightScript -Encoding UTF8

    $env:CODEX_DISPOSABLE_EXAM_NAME = $examName
    & node $playwrightScript

    $fallbackUiResults = Get-Content -Path $playwrightOutput -Raw | ConvertFrom-Json
    $examCheck = Invoke-RestMethod -Method Get -Headers $headers -Uri "$supabaseUrl/rest/v1/exams?id=eq.$createdExamId&select=id,force_stop"
    $sessionCheck = Invoke-RestMethod -Method Get -Headers $headers -Uri "$supabaseUrl/rest/v1/exam_sessions?id=eq.$createdSessionId&select=id,status,session_end"

    $report = [PSCustomObject]@{
        ui_results = @($localUiResults) + @($fallbackUiResults)
        fallback_db_check = [PSCustomObject]@{
            exam_force_stop = $examCheck[0].force_stop
            session_status = $sessionCheck[0].status
            session_end = $sessionCheck[0].session_end
        }
        background_jobs = [PSCustomObject]@{
            backend_state = if ($backendJob) { $backendJob.State } else { "Stopped before fallback validation" }
            local_dashboard_state = $localDashJob.State
        }
    }

    $report | ConvertTo-Json -Depth 8
}
finally {
    if ($createdSessionId) {
        try {
            Invoke-RestMethod -Method Delete -Headers $headers -Uri "$supabaseUrl/rest/v1/exam_sessions?id=eq.$createdSessionId" | Out-Null
        } catch {
        }
    }

    if ($createdExamId) {
        try {
            Invoke-RestMethod -Method Delete -Headers $headers -Uri "$supabaseUrl/rest/v1/exams?id=eq.$createdExamId" | Out-Null
        } catch {
        }
    }

    if (Test-Path $playwrightScript) {
        Remove-Item $playwrightScript -Force
    }

    if (Test-Path $playwrightOutput) {
        Remove-Item $playwrightOutput -Force
    }

    foreach ($job in @($backendJob, $localDashJob)) {
        if ($job) {
            try {
                Stop-Job -Job $job -ErrorAction SilentlyContinue | Out-Null
            } catch {
            }

            try {
                Remove-Job -Job $job -Force -ErrorAction SilentlyContinue | Out-Null
            } catch {
            }
        }
    }
}
