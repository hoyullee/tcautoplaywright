package com.sheets.automation;

import com.microsoft.playwright.*;
import com.microsoft.playwright.options.AriaRole;

public class PlaywrightExample {
    public static void main(String[] args) {
        try (Playwright playwright = Playwright.create()) {
            Browser browser = playwright.chromium().launch(new BrowserType.LaunchOptions()
                    .setHeadless(false));

            BrowserContext context = browser.newContext();
            Page page = context.newPage();

            // Navigate to Google
            page.navigate("https://www.google.com");
            System.out.println("Page title: " + page.title());

            // Take a screenshot
            page.screenshot(new Page.ScreenshotOptions()
                    .setPath(java.nio.file.Paths.get("screenshot.png")));
            System.out.println("Screenshot saved to screenshot.png");

            // Wait for a bit to see the browser
            page.waitForTimeout(2000);

            browser.close();
            System.out.println("Test completed successfully!");
        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
            e.printStackTrace();
        }
    }
}
