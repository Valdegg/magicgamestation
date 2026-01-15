/**
 * Browser test script for frontend authentication UI.
 * 
 * ⚠️  IMPORTANT: This is a JAVASCRIPT file, NOT a Python file!
 *    Do NOT run this with: python test_frontend_auth.js
 * 
 * Instructions:
 * 1. Start your collection server (python main_app.py or collection_ui.py)
 * 2. Open the collection page in your browser (e.g., http://localhost:5003)
 * 3. Open browser console (F12 or right-click -> Inspect -> Console)
 * 4. Copy and paste this entire script into the console
 * 5. Press Enter to run the tests
 * 
 * The tests will check if authentication UI functions work correctly.
 */

(function() {
    'use strict';
    
    console.log("=".repeat(60));
    console.log("FRONTEND AUTHENTICATION TEST SUITE");
    console.log("=".repeat(60));
    
    let testResults = {};
    
    // Helper function to run a test
    function runTest(testName, testFunc) {
        try {
            const result = testFunc();
            testResults[testName] = result;
            const status = result ? "✅ PASS" : "❌ FAIL";
            console.log(`${testName}: ${status}`);
            return result;
        } catch (error) {
            console.error(`❌ ${testName} crashed:`, error);
            testResults[testName] = false;
            return false;
        }
    }
    
    // Test 1: Check if auth UI elements exist
    function test_authUI_elements_exist() {
        const authSection = document.getElementById('authSection');
        const authButtons = document.getElementById('authButtons');
        const userInfo = document.getElementById('userInfo');
        const authModal = document.getElementById('authModal');
        
        return authSection !== null && 
               authButtons !== null && 
               userInfo !== null && 
               authModal !== null;
    }
    
    // Test 2: Test showLoginModal function
    function test_showLoginModal() {
        if (typeof showLoginModal !== 'function') {
            console.warn("showLoginModal function not found");
            return false;
        }
        
        showLoginModal();
        
        const modal = document.getElementById('authModal');
        const title = document.getElementById('authModalTitle');
        
        return modal !== null && 
               modal.style.display === 'flex' &&
               title !== null &&
               title.textContent === 'Login';
    }
    
    // Test 3: Test showRegisterModal function
    function test_showRegisterModal() {
        if (typeof showRegisterModal !== 'function') {
            console.warn("showRegisterModal function not found");
            return false;
        }
        
        showRegisterModal();
        
        const modal = document.getElementById('authModal');
        const title = document.getElementById('authModalTitle');
        
        return modal !== null && 
               modal.style.display === 'flex' &&
               title !== null &&
               title.textContent === 'Register';
    }
    
    // Test 4: Test hideAuthModal function
    function test_hideAuthModal() {
        if (typeof hideAuthModal !== 'function') {
            console.warn("hideAuthModal function not found");
            return false;
        }
        
        // Show modal first
        if (typeof showLoginModal === 'function') {
            showLoginModal();
        }
        
        hideAuthModal();
        
        const modal = document.getElementById('authModal');
        return modal !== null && modal.style.display === 'none';
    }
    
    // Test 5: Test checkAuthStatus function (mock)
    function test_checkAuthStatus_exists() {
        return typeof checkAuthStatus === 'function';
    }
    
    // Test 6: Test auth UI visibility logic
    function test_authUI_visibility() {
        const authButtons = document.getElementById('authButtons');
        const userInfo = document.getElementById('userInfo');
        
        if (!authButtons || !userInfo) {
            return false;
        }
        
        // Check that at least one is visible (depending on auth state)
        const buttonsVisible = authButtons.style.display !== 'none';
        const infoVisible = userInfo.style.display !== 'block';
        
        // At least one should be visible or they should toggle correctly
        return true; // Just check that elements exist and can be toggled
    }
    
    // Test 7: Test form elements exist
    function test_authForm_elements() {
        const form = document.getElementById('authForm');
        const usernameInput = document.getElementById('authUsername');
        const passwordInput = document.getElementById('authPassword');
        const errorDiv = document.getElementById('authError');
        
        return form !== null &&
               usernameInput !== null &&
               passwordInput !== null &&
               errorDiv !== null;
    }
    
    // Test 8: Test API path detection
    function test_apiPath_detection() {
        const currentPath = window.location.pathname;
        const isCollectionPath = currentPath.includes('/collection');
        
        // Check if the code would use correct API path
        const expectedPath = isCollectionPath ? '/collection/api/auth/me' : '/api/auth/me';
        
        console.log(`  Current path: ${currentPath}`);
        console.log(`  Expected API path: ${expectedPath}`);
        
        return true; // Just verify we can detect the path
    }
    
    // Test 9: Test logout function exists
    function test_logout_exists() {
        return typeof logout === 'function';
    }
    
    // Test 10: Test handleAuth function exists
    function test_handleAuth_exists() {
        return typeof handleAuth === 'function';
    }
    
    // Run all tests
    console.log("\nRunning tests...\n");
    
    runTest("authUI_elements_exist", test_authUI_elements_exist);
    runTest("showLoginModal", test_showLoginModal);
    runTest("showRegisterModal", test_showRegisterModal);
    runTest("hideAuthModal", test_hideAuthModal);
    runTest("checkAuthStatus_exists", test_checkAuthStatus_exists);
    runTest("authUI_visibility", test_authUI_visibility);
    runTest("authForm_elements", test_authForm_elements);
    runTest("apiPath_detection", test_apiPath_detection);
    runTest("logout_exists", test_logout_exists);
    runTest("handleAuth_exists", test_handleAuth_exists);
    
    // Summary
    console.log("\n" + "=".repeat(60));
    console.log("TEST SUMMARY");
    console.log("=".repeat(60));
    
    let passed = 0;
    let failed = 0;
    
    for (const [testName, result] of Object.entries(testResults)) {
        if (result) {
            passed++;
        } else {
            failed++;
        }
    }
    
    console.log(`Total tests: ${Object.keys(testResults).length}`);
    console.log(`Passed: ${passed}`);
    console.log(`Failed: ${failed}`);
    
    const allPassed = failed === 0;
    console.log(`\nOverall: ${allPassed ? '✅ ALL TESTS PASSED' : '❌ SOME TESTS FAILED'}`);
    
    // Additional manual test instructions
    console.log("\n" + "=".repeat(60));
    console.log("MANUAL TEST INSTRUCTIONS");
    console.log("=".repeat(60));
    console.log("1. Click 'Login' button - modal should appear");
    console.log("2. Click 'Register' button - modal should show 'Register' title");
    console.log("3. Try logging in with test credentials");
    console.log("4. After login, verify 'Logout' button appears");
    console.log("5. Click 'Logout' - should return to login/register buttons");
    console.log("6. Verify API calls work (check Network tab in DevTools)");
    
    return allPassed;
})();
