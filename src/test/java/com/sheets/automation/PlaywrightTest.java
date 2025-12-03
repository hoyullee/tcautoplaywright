package com.sheets.automation;

import com.microsoft.playwright.*;
import org.junit.jupiter.api.*;

import static org.junit.jupiter.api.Assertions.*;

public class PlaywrightTest {
    private static Playwright playwright;
    private static Browser browser;
    private BrowserContext context;
    private Page page;

    @BeforeAll
    static void launchBrowser() {
        playwright = Playwright.create();
        browser = playwright.chromium().launch(new BrowserType.LaunchOptions()
                .setHeadless(true));
    }

    @AfterAll
    static void closeBrowser() {
        if (browser != null) {
            browser.close();
        }
        if (playwright != null) {
            playwright.close();
        }
    }

    @BeforeEach
    void createContextAndPage() {
        context = browser.newContext();
        page = context.newPage();
    }

    @AfterEach
    void closeContext() {
        if (context != null) {
            context.close();
        }
    }

    @Test
    void testGoogleHomePage() {
        page.navigate("https://www.google.com");

        // Verify the title contains "Google"
        String title = page.title();
        assertTrue(title.contains("Google"), "Page title should contain 'Google'");

        System.out.println("Test passed! Page title: " + title);
    }

    @Test
    void testExampleDotCom() {
        page.navigate("https://example.com");

        // Verify we can find the heading
        Locator heading = page.locator("h1");
        assertTrue(heading.isVisible(), "Heading should be visible");

        String headingText = heading.textContent();
        assertEquals("Example Domain", headingText, "Heading text should be 'Example Domain'");

        System.out.println("Test passed! Heading text: " + headingText);
    }
}
