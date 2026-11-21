import { test, expect } from "@playwright/test";

test.describe("Phase 16 E2E: Evidence Report, PDF Export & Cryptographic Verification", () => {
  test("should load the public verification page with cryptographic disclaimers", async ({ page }) => {
    await page.goto("/verify");

    // Header assertions
    await expect(page.getByText(/Verify Report Authenticity|التحقق من صحة تقرير/i)).toBeVisible();
    await expect(page.getByText(/without exposing any patient PHI|دون الكشف عن أي بيانات شخصية/i)).toBeVisible();

    // Input and Verify button
    const refInput = page.getByPlaceholder(/GNX-RPT-/i);
    await expect(refInput).toBeVisible();

    const verifyBtn = page.getByRole("button", { name: /Verify|تحقق/i });
    await expect(verifyBtn).toBeDisabled(); // Disabled until reference entered
  });

  test("should handle valid report reference verification", async ({ page }) => {
    // Mock the verification endpoint matching ReportVerificationResponse schema
    await page.route("**/api/v1/reports/GNX-RPT-2026-TEST01/verify", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          report_reference: "GNX-RPT-2026-TEST01",
          is_valid: true,
          status: "VERIFIED",
          message_en: "Cryptographic signature matches authoritative release.",
          message_ar: "التوقيع الرقمي مطابق للإصدار المعتمد للتقرير.",
          generated_at: "2026-11-20T12:00:00Z",
          questionnaire_version_tag: "v1.0",
          rule_engine_version: "v2.4.0",
          outcome_tier: "URGENT_MEDICAL_ASSESSMENT",
          cryptographic_hash: "8f4a7c2b9e1d3f5a7c2b9e1d3f5a7c2b9e1d3f5a7c2b9e1d3f5a7c2b9e1d3f5a",
        }),
      });
    });

    await page.goto("/verify?ref=GNX-RPT-2026-TEST01");

    // Verification result should display
    await expect(page.getByText(/Authentic & Verified Report|تقرير أصلي موثق/i)).toBeVisible();
    await expect(page.getByText(/v2.4.0/)).toBeVisible();
    await expect(page.getByText("GNX-RPT-2026-TEST01")).toBeVisible();
  });

  test("should handle invalid or unverified report reference verification", async ({ page }) => {
    // Intercept invalid report verification
    await page.route("**/api/v1/reports/GNX-RPT-INVALID-999/verify", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          report_reference: "GNX-RPT-INVALID-999",
          is_valid: false,
          status: "UNVERIFIED",
          message_en: "Report reference not found or cryptographic signature invalid.",
          message_ar: "الرقم المرجعي للتقرير غير موجود أو التوقيع الرقمي غير صالح.",
          generated_at: null,
          questionnaire_version_tag: null,
          rule_engine_version: null,
          outcome_tier: null,
          cryptographic_hash: null,
        }),
      });
    });

    await page.goto("/verify?ref=GNX-RPT-INVALID-999");

    // Assert that the page displays the unverified status alert
    await expect(
      page.getByText(/Unverified Report|not found|signature invalid|غير موثق|غير صالح/i)
    ).toBeVisible();
  });

  test("should trigger actual PDF download, verify PDF signature, and inspect file content", async ({ page }) => {
    // Standard valid PDF file stream payload containing report details
    const validPdfPayload = Buffer.from(
      "%PDF-1.4\n" +
      "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n" +
      "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n" +
      "3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R >>\nendobj\n" +
      "4 0 obj\n<< /Length 180 >>\nstream\nBT\n/F1 12 Tf\n50 780 Td\n" +
      "(GENOVEX CLINICAL ASSESSMENT REPORT) Tj\n" +
      "0 -20 Td\n(Report Reference: GNX-RPT-2026-888999) Tj\n" +
      "0 -20 Td\n(Outcome: SPECIALIST_EVALUATION_RECOMMENDED) Tj\n" +
      "ET\nendstream\nendobj\n" +
      "xref\n0 5\n0000000000 65535 f \n0000000010 00000 n \n0000000059 00000 n \n0000000116 00000 n \n0000000207 00000 n \n" +
      "trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n440\n%%EOF\n"
    );

    // Mock report summary metadata
    const mockReportData = {
      id: 1,
      session_token: "test_session_token_123",
      report_reference: "GNX-RPT-2026-888999",
      overall_tier: "SPECIALIST_EVALUATION_RECOMMENDED",
      overall_score: 65.0,
      condition_title_en: "Male Factor Infertility",
      condition_title_ar: "عوامل العقم عند الذكور",
      is_evaluation_incomplete: false,
      evidence_citations: [
        {
          id: 1,
          source_title: "EAU Guidelines on Sexual and Reproductive Health (2024)",
          doi: "10.1016/j.eururo.2023.01.001",
          evidence_level: "Level 1A",
        },
      ],
      created_at: "2026-11-20T10:00:00Z",
    };

    await page.route("**/questionnaire/assessments/test_session_token_123/report", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockReportData),
      });
    });

    await page.route("**/api/v1/assessment/test_session_token_123/report", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockReportData),
      });
    });

    await page.route("**/api/v1/assessment/test_session_token_123/navigation-recommendations", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          overall_tier: "SPECIALIST_EVALUATION_RECOMMENDED",
          urgency_window_hours: 48,
          facilities: [],
        }),
      });
    });

    // Mock the PDF download endpoints returning real PDF bytes
    const pdfResponseHandler = async (route: any) => {
      await route.fulfill({
        status: 200,
        contentType: "application/pdf",
        headers: {
          "Content-Disposition": 'attachment; filename="GENOVEX-Report-GNX-RPT-2026-888999.pdf"',
          "Content-Type": "application/pdf",
        },
        body: validPdfPayload,
      });
    };

    await page.route("**/assessment/*/report/pdf*", pdfResponseHandler);
    await page.route("**/api/v1/assessment/*/report/pdf*", pdfResponseHandler);

    await page.goto("/assessment/report/test_session_token_123");

    // Locate the Download PDF trigger
    const downloadBtn = page.getByRole("button", { name: /Download PDF|تحميل التقرير/i });
    await expect(downloadBtn).toBeVisible();

    // Verify parent anchor tag has download and proper endpoint URL
    const downloadLink = page.locator("a[download]");
    await expect(downloadLink).toBeVisible();
    await expect(downloadLink).toHaveAttribute(
      "href",
      /\/assessment\/test_session_token_123\/report\/pdf/
    );

    // Remove target="_blank" before triggering click to ensure the download is captured directly on current page
    await page.evaluate(() => {
      const link = document.querySelector("a[download]");
      if (link) link.removeAttribute("target");
    });

    // Trigger and capture the actual browser download event
    const downloadPromise = page.waitForEvent("download");
    await downloadBtn.click();
    const download = await downloadPromise;

    // 1. Verify suggested filename
    expect(download.suggestedFilename()).toBe("GENOVEX-Report-GNX-RPT-2026-888999.pdf");

    // 2. Read downloaded stream into memory
    const stream = await download.createReadStream();
    expect(stream).not.toBeNull();

    const chunks: Buffer[] = [];
    for await (const chunk of stream!) {
      chunks.push(Buffer.from(chunk));
    }
    const downloadedBuffer = Buffer.concat(chunks);

    // 3. Verify magic bytes: PDF signature "%PDF-" at index 0
    const magicHeader = downloadedBuffer.toString("utf-8", 0, 5);
    expect(magicHeader).toBe("%PDF-");

    // 4. Verify EOF trailer
    const trailerEnd = downloadedBuffer.toString("utf-8");
    expect(trailerEnd).toContain("%%EOF");

    // 5. Verify payload contains expected report reference and non-empty byte stream
    expect(downloadedBuffer.length).toBeGreaterThan(100);
    expect(trailerEnd).toContain("GNX-RPT-2026-888999");
    expect(trailerEnd).toContain("GENOVEX CLINICAL ASSESSMENT REPORT");

    // Verify Print button is also available
    const printBtn = page.getByRole("button", { name: /print|طباعة/i });
    await expect(printBtn).toBeVisible();
  });
});
