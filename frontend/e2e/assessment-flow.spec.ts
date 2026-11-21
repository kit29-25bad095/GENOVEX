import { test, expect } from "@playwright/test";

test.describe("Phase 16 E2E: Clinical Assessment Wizard Flow", () => {
  test("should render adaptive assessment questions, handle safe options and trigger red-flag emergency alert", async ({ page }) => {
    // Mock the start assessment endpoint (handles both routes)
    const startData = {
      assessment_id: "test_asmt_12345",
      session_token: "test_token_12345",
      current_domain_index: 0,
      total_domains: 2,
      domain_id: "general_health",
      domain_title_en: "General Health & Demographics",
      domain_title_ar: "الصحة العامة والبيانات الأساسية",
    };

    await page.route("**/questionnaire/assessments/start", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(startData),
      });
    });

    await page.route("**/api/v1/assessment/start", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(startData),
      });
    });

    // Mock domain questions with standard questions and acute red-flag question
    const domainData = {
      domain_id: "general_health",
      domain_title_en: "General Health & Demographics",
      domain_title_ar: "الصحة العامة والبيانات الأساسية",
      domain_index: 0,
      total_domains: 2,
      questions: [
        {
          id: "Q101",
          question_code: "AGE_GROUP",
          question_text_en: "What is your age group?",
          question_text_ar: "ما هي فئتك العمرية؟",
          question_type: "SINGLE_CHOICE",
          options: [
            { value: "18_24", label_en: "18 - 24", label_ar: "18 - 24" },
            { value: "25_34", label_en: "25 - 34", label_ar: "25 - 34" },
            { value: "35_44", label_en: "35 - 44", label_ar: "35 - 44" },
          ],
          allow_unsure: true,
          allow_prefer_not_to_say: true,
        },
        {
          id: "Q_ACUTE_SCROTAL_PAIN",
          question_code: "Q_ACUTE_SCROTAL_PAIN",
          question_text_en: "Are you experiencing sudden, severe testicular pain?",
          question_text_ar: "هل تعاني من ألم حاد ومفاجئ في الخصية؟",
          question_type: "SINGLE_CHOICE",
          options: [
            { value: "yes", label_en: "Yes", label_ar: "نعم" },
            { value: "no", label_en: "No", label_ar: "لا" },
          ],
          allow_unsure: false,
          allow_prefer_not_to_say: false,
        },
      ],
      saved_responses: {},
    };

    await page.route("**/questionnaire/assessments/**/domain/**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(domainData),
      });
    });

    await page.route("**/api/v1/assessment/**/domain/**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(domainData),
      });
    });

    await page.goto("/assessment");

    // Question heading should be rendered
    await expect(page.getByText("What is your age group?")).toBeVisible();

    // Standard options should be clickable
    const option1 = page.getByRole("button", { name: "25 - 34" });
    await expect(option1).toBeVisible();
    await option1.click();

    // Verify safe options exist ("Not Sure" and "Prefer Not to Say") on first question
    const unsureBtn = page.getByRole("button", { name: /Not Sure|غير متأكد/i }).first();
    await expect(unsureBtn).toBeVisible();

    const preferNotBtn = page.getByRole("button", { name: /Prefer Not to Say|أفضل عدم الإجابة/i }).first();
    await expect(preferNotBtn).toBeVisible();

    // Select safe answer
    await unsureBtn.click();

    // Test real-time urgent red flag trigger
    const acutePainYesBtn = page.getByRole("button", { name: /^Yes$|^نعم$/i });
    await expect(acutePainYesBtn).toBeVisible();
    await acutePainYesBtn.click();

    // Live emergency warning banner should immediately trigger
    await expect(page.getByText(/Emergency warning|within 6 hours|طوارئ/i)).toBeVisible();
  });

  test("should complete domain progression, pre-submission review and report transition", async ({ page }) => {
    const startData = {
      assessment_id: "test_asmt_full_flow",
      session_token: "test_token_full_flow",
      current_domain_index: 0,
      total_domains: 1,
      domain_id: "domain_1",
      domain_title_en: "Fertility History",
      domain_title_ar: "تاريخ الخصوبة",
    };

    await page.route("**/questionnaire/assessments/start", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(startData),
      });
    });

    await page.route("**/api/v1/assessment/start", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(startData),
      });
    });

    const domainData = {
      domain_id: "domain_1",
      domain_title_en: "Fertility History",
      domain_title_ar: "تاريخ الخصوبة",
      domain_index: 0,
      total_domains: 1,
      questions: [
        {
          id: "Q_FERT_DURATION",
          question_code: "Q_FERT_DURATION",
          question_text_en: "How long have you been trying to conceive?",
          question_text_ar: "منذ متى وأنتما تحاولان الإنجاب؟",
          question_type: "SINGLE_CHOICE",
          options: [
            { value: "less_6m", label_en: "< 6 months", label_ar: "أقل من 6 أشهر" },
            { value: "over_12m", label_en: "12+ months", label_ar: "أكثر من 12 شهرًا" },
          ],
          allow_unsure: true,
          allow_prefer_not_to_say: true,
        },
      ],
      saved_responses: {},
    };

    await page.route("**/questionnaire/assessments/**/domain/**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(domainData),
      });
    });

    await page.route("**/api/v1/assessment/**/domain/**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(domainData),
      });
    });

    // Mock save responses across all possible endpoint patterns
    const saveResponseMock = async (route: any) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ status: "saved", saved_count: 1 }),
      });
    };
    await page.route("**/questionnaire/assessments/**/save*", saveResponseMock);
    await page.route("**/api/v1/assessment/**/save*", saveResponseMock);
    await page.route("**/questionnaire/assessments/**/domain/**/responses", saveResponseMock);
    await page.route("**/api/v1/assessment/**/domain/**/responses", saveResponseMock);

    // Mock review data when entering pre-submission review mode matching AssessmentReviewResponse
    const reviewData = {
      assessment_id: "test_asmt_full_flow",
      session_token: "test_token_full_flow",
      status: "IN_PROGRESS",
      version_tag: "v1.0.0",
      current_domain_index: 0,
      progress_percentage: 100,
      total_questions: 1,
      answered_count: 1,
      unanswered_required_count: 0,
      can_submit: true,
      urgent_red_flags: [],
      domains: [
        {
          domain_code: "domain_1",
          domain_index: 0,
          domain_title_en: "Fertility History",
          domain_title_ar: "تاريخ الخصوبة",
          is_complete: true,
          questions: [
            {
              question_id: 101,
              question_key: "Q_FERT_DURATION",
              question_code: "Q_FERT_DURATION",
              text_en: "How long have you been trying to conceive?",
              text_ar: "منذ متى وأنتما تحاولان الإنجاب؟",
              answer_value: "over_12m",
              is_unsure: false,
              is_prefer_not_to_say: false,
              conditional_pathway_active: true,
              needs_reconfirmation: false,
              is_answered: true,
              is_required: true,
              is_urgent_red_flag: false,
              domain_code: "domain_1",
            },
          ],
        },
      ],
    };

    const reviewResponseMock = async (route: any) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(reviewData),
      });
    };
    await page.route("**/questionnaire/assessments/**/review", reviewResponseMock);
    await page.route("**/api/v1/assessment/**/review", reviewResponseMock);

    // Mock final submission & evaluation endpoints
    const submitResponseMock = async (route: any) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ status: "SUBMITTED", assessment_id: "test_asmt_full_flow" }),
      });
    };
    await page.route("**/questionnaire/assessments/**/submit", submitResponseMock);
    await page.route("**/api/v1/assessment/**/submit", submitResponseMock);

    const evaluateResponseMock = async (route: any) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "EVALUATED",
          report_reference: "GNX-RPT-2026-EVAL01",
          overall_tier: "SPECIALIST_EVALUATION_RECOMMENDED",
        }),
      });
    };
    await page.route("**/questionnaire/assessments/**/evaluate", evaluateResponseMock);
    await page.route("**/api/v1/assessment/**/evaluate", evaluateResponseMock);

    await page.goto("/assessment");

    // Select answer
    const choiceBtn = page.getByRole("button", { name: "12+ months" });
    await expect(choiceBtn).toBeVisible();
    await choiceBtn.click();

    // Click Next/Review to proceed to pre-submission review
    const nextBtn = page.getByRole("button", { name: /Next|Review|التالي|مراجعة/i });
    await expect(nextBtn).toBeEnabled();
    await nextBtn.click();

    // In review mode, pre-submission review card should be visible
    await expect(page.getByText(/Pre-Submission Review|مراجعة الاستبيان/i).first()).toBeVisible();

    // Submit assessment & View Report
    const submitBtn = page.getByRole("button", { name: /Submit Assessment & View Report|اعتماد التقييم/i });
    await expect(submitBtn).toBeEnabled();
    await submitBtn.click();

    // Expect transition to report route
    await expect(page).toHaveURL(/\/assessment\/report\/test_token_full_flow/);
  });
});
